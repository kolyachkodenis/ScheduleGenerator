"""Persistent manual timetable editing with versions, locks, and comparison."""

from __future__ import annotations

import copy
import json
import uuid
from dataclasses import dataclass
from typing import Any, Callable

from schedule_generator.api import GenerationOptions, GenerationResult, SchedulingProblem, generate_schedule
from schedule_generator.jobs import AssignmentValidator, _default_assignment_validator
from schedule_generator.quality import evaluate_quality
from schedule_generator.storage import DatasetStore


QualityEvaluator = Callable[[dict[str, Any], list[dict[str, Any]]], dict[str, Any]]


@dataclass(frozen=True)
class DraftVersion:
    version: int
    assignments: list[dict[str, Any]]
    quality: dict[str, Any] | None
    validation_errors: tuple[str, ...]
    change: dict[str, Any]
    created_at: str


@dataclass(frozen=True)
class TimetableDraft:
    draft_id: str
    job_id: str
    dataset_id: str
    dataset_revision: int
    current_version: int
    latest_version: int
    locked_assignment_ids: tuple[str, ...]
    version: DraftVersion
    history: tuple[dict[str, Any], ...]


class TimetableEditingService:
    """Manage editable timetable versions while preserving generated results."""

    def __init__(
        self,
        store: DatasetStore,
        validator: AssignmentValidator = _default_assignment_validator,
        quality_evaluator: QualityEvaluator = evaluate_quality,
        generator: Callable[[SchedulingProblem, GenerationOptions], GenerationResult] = generate_schedule,
    ) -> None:
        self.store = store
        self.validator = validator
        self.quality_evaluator = quality_evaluator
        self.generator = generator

    def create_from_job(self, job_id: str) -> TimetableDraft:
        job = self.store.connection.execute(
            "SELECT * FROM generation_jobs WHERE job_id = ?", (job_id,)
        ).fetchone()
        if job is None:
            raise KeyError(job_id)
        if job["status"] != "SUCCEEDED" or not job["result_json"]:
            raise ValueError("only a successful generation job can be edited")
        existing = self.store.connection.execute(
            "SELECT draft_id FROM timetable_drafts WHERE job_id = ?", (job_id,)
        ).fetchone()
        if existing:
            return self.get(existing[0])
        result = json.loads(job["result_json"])
        draft_id = uuid.uuid4().hex
        with self.store.connection:
            self.store.connection.execute(
                "INSERT INTO timetable_drafts(draft_id, job_id, dataset_id, dataset_revision) "
                "VALUES (?, ?, ?, ?)",
                (draft_id, job_id, job["dataset_id"], job["dataset_revision"]),
            )
            self.store.connection.execute(
                """
                INSERT INTO timetable_draft_versions(
                    draft_id, version, assignments_json, quality_json,
                    validation_errors_json, change_json
                ) VALUES (?, 0, ?, ?, ?, ?)
                """,
                (
                    draft_id,
                    json.dumps(result["assignments"], sort_keys=True),
                    json.dumps(result.get("quality_report"), sort_keys=True),
                    json.dumps(result.get("validation_errors", [])),
                    json.dumps({"type": "generated", "job_id": job_id}),
                ),
            )
        return self.get(draft_id)

    def get(self, draft_id: str) -> TimetableDraft:
        draft = self.store.connection.execute(
            "SELECT * FROM timetable_drafts WHERE draft_id = ?", (draft_id,)
        ).fetchone()
        if draft is None:
            raise KeyError(draft_id)
        rows = self.store.connection.execute(
            "SELECT version, change_json, created_at FROM timetable_draft_versions "
            "WHERE draft_id = ? ORDER BY version", (draft_id,)
        ).fetchall()
        current = self._version(draft_id, int(draft["current_version"]))
        locks = self.store.connection.execute(
            "SELECT assignment_id FROM timetable_locks WHERE draft_id = ? "
            "ORDER BY assignment_id", (draft_id,)
        ).fetchall()
        return TimetableDraft(
            draft_id=draft_id,
            job_id=draft["job_id"],
            dataset_id=draft["dataset_id"],
            dataset_revision=int(draft["dataset_revision"]),
            current_version=int(draft["current_version"]),
            latest_version=int(rows[-1]["version"]),
            locked_assignment_ids=tuple(row[0] for row in locks),
            version=current,
            history=tuple(
                {
                    "version": int(row["version"]),
                    "change": json.loads(row["change_json"]),
                    "created_at": row["created_at"],
                }
                for row in rows
            ),
        )

    def list(self) -> list[TimetableDraft]:
        rows = self.store.connection.execute(
            "SELECT draft_id FROM timetable_drafts ORDER BY created_at, draft_id"
        ).fetchall()
        return [self.get(row[0]) for row in rows]

    def _version(self, draft_id: str, version: int) -> DraftVersion:
        row = self.store.connection.execute(
            "SELECT * FROM timetable_draft_versions WHERE draft_id = ? AND version = ?",
            (draft_id, version),
        ).fetchone()
        if row is None:
            raise KeyError(f"{draft_id}@{version}")
        return DraftVersion(
            version=version,
            assignments=json.loads(row["assignments_json"]),
            quality=json.loads(row["quality_json"]) if row["quality_json"] else None,
            validation_errors=tuple(json.loads(row["validation_errors_json"])),
            change=json.loads(row["change_json"]),
            created_at=row["created_at"],
        )

    def move(
        self,
        draft_id: str,
        assignment_id: str,
        day_id: str,
        period_id: str,
        teacher_id: str | None = None,
        classroom_id: str | None = None,
    ) -> TimetableDraft:
        draft = self.get(draft_id)
        if assignment_id in draft.locked_assignment_ids:
            raise ValueError("locked assignments cannot be moved")
        assignments = copy.deepcopy(draft.version.assignments)
        assignment = next(
            (item for item in assignments if item["id"] == assignment_id), None
        )
        if assignment is None:
            raise KeyError(assignment_id)
        dataset = self.store.get(draft.dataset_id, draft.dataset_revision).data
        periods = [
            item["id"]
            for item in sorted(
                dataset["academic_period"]["periods"], key=lambda item: item["ordinal"]
            )
        ]
        try:
            start = periods.index(period_id)
        except ValueError as error:
            raise ValueError(f"unknown period {period_id!r}") from error
        length = len(assignment["occupied_period_ids"])
        occupied = periods[start : start + length]
        if len(occupied) != length:
            raise ValueError("lesson block does not fit after the selected period")
        before = copy.deepcopy(assignment)
        assignment["slot"] = {"day_id": day_id, "period_id": period_id}
        assignment["occupied_period_ids"] = occupied
        if teacher_id is not None:
            assignment["teacher_id"] = teacher_id
        if classroom_id is not None:
            assignment["classroom_id"] = classroom_id
        return self._append(
            draft,
            assignments,
            {
                "type": "move",
                "assignment_id": assignment_id,
                "before": before,
                "after": assignment,
            },
        )

    def set_lock(
        self, draft_id: str, assignment_id: str, locked: bool
    ) -> TimetableDraft:
        draft = self.get(draft_id)
        if not any(item["id"] == assignment_id for item in draft.version.assignments):
            raise KeyError(assignment_id)
        with self.store.connection:
            if locked:
                self.store.connection.execute(
                    "INSERT OR IGNORE INTO timetable_locks(draft_id, assignment_id) VALUES (?, ?)",
                    (draft_id, assignment_id),
                )
            else:
                self.store.connection.execute(
                    "DELETE FROM timetable_locks WHERE draft_id = ? AND assignment_id = ?",
                    (draft_id, assignment_id),
                )
        return self.get(draft_id)

    def undo(self, draft_id: str) -> TimetableDraft:
        draft = self.get(draft_id)
        if draft.current_version == 0:
            raise ValueError("nothing to undo")
        return self._select_version(draft_id, draft.current_version - 1)

    def redo(self, draft_id: str) -> TimetableDraft:
        draft = self.get(draft_id)
        if draft.current_version >= draft.latest_version:
            raise ValueError("nothing to redo")
        return self._select_version(draft_id, draft.current_version + 1)

    def _select_version(self, draft_id: str, version: int) -> TimetableDraft:
        self._version(draft_id, version)
        with self.store.connection:
            self.store.connection.execute(
                "UPDATE timetable_drafts SET current_version = ?, updated_at = CURRENT_TIMESTAMP "
                "WHERE draft_id = ?", (version, draft_id)
            )
        return self.get(draft_id)

    def _append(
        self,
        draft: TimetableDraft,
        assignments: list[dict[str, Any]],
        change: dict[str, Any],
        quality: dict[str, Any] | None = None,
    ) -> TimetableDraft:
        dataset = self.store.get(draft.dataset_id, draft.dataset_revision).data
        errors = self.validator(dataset, assignments)
        quality = quality or self.quality_evaluator(dataset, assignments)
        version = draft.current_version + 1
        with self.store.connection:
            self.store.connection.execute(
                "DELETE FROM timetable_draft_versions WHERE draft_id = ? AND version >= ?",
                (draft.draft_id, version),
            )
            self.store.connection.execute(
                """
                INSERT INTO timetable_draft_versions(
                    draft_id, version, assignments_json, quality_json,
                    validation_errors_json, change_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    draft.draft_id,
                    version,
                    json.dumps(assignments, sort_keys=True),
                    json.dumps(quality, sort_keys=True),
                    json.dumps(errors),
                    json.dumps(change, sort_keys=True),
                ),
            )
            self.store.connection.execute(
                "UPDATE timetable_drafts SET current_version = ?, updated_at = CURRENT_TIMESTAMP "
                "WHERE draft_id = ?", (version, draft.draft_id)
            )
        return self.get(draft.draft_id)

    def regenerate(
        self, draft_id: str, options: GenerationOptions | None = None
    ) -> TimetableDraft:
        draft = self.get(draft_id)
        dataset = self.store.get(draft.dataset_id, draft.dataset_revision).data
        locked = {
            item["id"]: item
            for item in draft.version.assignments
            if item["id"] in draft.locked_assignment_ids
        }
        fixed_by_occurrence = {
            (item["requirement_id"], item["occurrence_index"]): item
            for item in dataset["fixed_lessons"]
        }
        for assignment in locked.values():
            fixed_by_occurrence[
                (assignment["requirement_id"], assignment["occurrence_index"])
            ] = {
                "id": f"locked_{assignment['id']}",
                "requirement_id": assignment["requirement_id"],
                "occurrence_index": assignment["occurrence_index"],
                "slot": assignment["slot"],
                "teacher_id": assignment["teacher_id"],
                "classroom_id": assignment["classroom_id"],
            }
        dataset["fixed_lessons"] = list(fixed_by_occurrence.values())
        result = self.generator(
            SchedulingProblem.from_mapping(dataset), options or GenerationOptions()
        )
        if not result.is_success:
            raise ValueError(
                "regeneration failed: "
                + "; ".join(item.message for item in result.diagnostics)
            )
        payload = result.to_dict()
        return self._append(
            draft,
            payload["assignments"],
            {
                "type": "regenerate",
                "locked_assignment_ids": sorted(locked),
                "seed": (options or GenerationOptions()).seed,
            },
            payload["quality_report"],
        )

    def compare(self, draft_id: str, left: int, right: int) -> dict[str, Any]:
        left_version = self._version(draft_id, left)
        right_version = self._version(draft_id, right)
        left_by_id = {item["id"]: item for item in left_version.assignments}
        right_by_id = {item["id"]: item for item in right_version.assignments}
        changes = []
        for assignment_id in sorted(set(left_by_id) | set(right_by_id)):
            before = left_by_id.get(assignment_id)
            after = right_by_id.get(assignment_id)
            if before != after:
                changes.append(
                    {"assignment_id": assignment_id, "before": before, "after": after}
                )
        left_penalty = (left_version.quality or {}).get("total_penalty")
        right_penalty = (right_version.quality or {}).get("total_penalty")
        return {
            "left": left,
            "right": right,
            "changes": changes,
            "quality_delta": (
                right_penalty - left_penalty
                if left_penalty is not None and right_penalty is not None
                else None
            ),
            "validation_error_delta": len(right_version.validation_errors)
            - len(left_version.validation_errors),
        }
