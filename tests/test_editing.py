from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from schedule_generator.api import GenerationOptions, GenerationResult, SchedulingProblem
from schedule_generator.editing import TimetableEditingService
from schedule_generator.jobs import GenerationRequest, SchedulingService
from schedule_generator.quality import evaluate_quality
from schedule_generator.storage import DatasetStore


ROOT = Path(__file__).resolve().parents[1]
DEMO = json.loads((ROOT / "examples" / "small-school.json").read_text(encoding="utf-8"))


def assignments() -> list[dict]:
    return [
        {
            "id": "req_joint_advisory__0",
            "requirement_id": "req_joint_advisory",
            "occurrence_index": 0,
            "slot": {"day_id": "mon", "period_id": "p1"},
            "occupied_period_ids": ["p1"],
            "teacher_id": "t_art",
            "classroom_id": "hall",
        },
        {
            "id": "req_7a_math__0",
            "requirement_id": "req_7a_math",
            "occurrence_index": 0,
            "slot": {"day_id": "mon", "period_id": "p2"},
            "occupied_period_ids": ["p2"],
            "teacher_id": "t_math",
            "classroom_id": "room_101",
        },
    ]


def result_for(problem: SchedulingProblem, _options: GenerationOptions) -> GenerationResult:
    return GenerationResult.from_backend(
        problem,
        {
            "status": "FEASIBLE",
            "assignments": assignments(),
            "quality_report": {
                "total_penalty": 10,
                "by_constraint": {},
                "violations": [],
            },
            "diagnostics": [],
            "validation_errors": [],
        },
    )


def validator(_dataset: dict, items: list[dict]) -> list[str]:
    slots = [(item["slot"]["day_id"], item["slot"]["period_id"]) for item in items]
    return ["student collision"] if len(slots) != len(set(slots)) else []


def quality(_dataset: dict, items: list[dict]) -> dict:
    penalty = sum(5 for item in items if item["slot"]["day_id"] == "tue")
    return {"total_penalty": penalty, "by_constraint": {}, "violations": []}


class TimetableEditingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.store = DatasetStore(Path(self.temporary.name) / "school.db")
        self.store.save(DEMO)
        jobs = SchedulingService(self.store, result_for)
        job = jobs.create_job(GenerationRequest(DEMO["dataset_id"]))
        self.job = jobs.run_job(job.job_id)
        self.editing = TimetableEditingService(
            self.store, validator=validator, quality_evaluator=quality, generator=result_for
        )
        self.draft = self.editing.create_from_job(self.job.job_id)

    def tearDown(self) -> None:
        self.store.close()
        self.temporary.cleanup()

    def test_move_creates_version_and_recalculates_quality(self) -> None:
        moved = self.editing.move(
            self.draft.draft_id, "req_7a_math__0", "tue", "p2"
        )
        self.assertEqual(moved.current_version, 1)
        self.assertEqual(moved.version.quality["total_penalty"], 5)
        self.assertEqual(moved.version.validation_errors, ())
        comparison = self.editing.compare(self.draft.draft_id, 0, 1)
        self.assertEqual(len(comparison["changes"]), 1)
        self.assertEqual(comparison["quality_delta"], -5)

    def test_invalid_move_is_saved_with_immediate_conflict(self) -> None:
        moved = self.editing.move(
            self.draft.draft_id, "req_7a_math__0", "mon", "p1"
        )
        self.assertEqual(moved.version.validation_errors, ("student collision",))

    def test_undo_redo_and_branching_history(self) -> None:
        moved = self.editing.move(
            self.draft.draft_id, "req_7a_math__0", "tue", "p2"
        )
        self.assertEqual(self.editing.undo(moved.draft_id).current_version, 0)
        self.assertEqual(self.editing.redo(moved.draft_id).current_version, 1)
        self.editing.undo(moved.draft_id)
        branched = self.editing.move(
            moved.draft_id, "req_7a_math__0", "wed", "p2"
        )
        self.assertEqual(branched.latest_version, 1)
        self.assertEqual(len(branched.history), 2)

    def test_locked_assignment_cannot_move(self) -> None:
        locked = self.editing.set_lock(
            self.draft.draft_id, "req_7a_math__0", True
        )
        self.assertIn("req_7a_math__0", locked.locked_assignment_ids)
        with self.assertRaisesRegex(ValueError, "locked assignments"):
            self.editing.move(
                self.draft.draft_id, "req_7a_math__0", "tue", "p2"
            )
        unlocked = self.editing.set_lock(
            self.draft.draft_id, "req_7a_math__0", False
        )
        self.assertNotIn("req_7a_math__0", unlocked.locked_assignment_ids)

    def test_regeneration_converts_locks_to_fixed_lessons(self) -> None:
        self.editing.set_lock(self.draft.draft_id, "req_7a_math__0", True)
        seen: list[dict] = []

        def generator(
            problem: SchedulingProblem, options: GenerationOptions
        ) -> GenerationResult:
            seen.extend(problem.to_mapping()["fixed_lessons"])
            return result_for(problem, options)

        editing = TimetableEditingService(
            self.store, validator=validator, quality_evaluator=quality, generator=generator
        )
        regenerated = editing.regenerate(
            self.draft.draft_id, GenerationOptions(seed=9)
        )
        self.assertEqual(regenerated.version.change["type"], "regenerate")
        self.assertTrue(
            any(item["requirement_id"] == "req_7a_math" for item in seen)
        )
        self.assertTrue(
            any(item["requirement_id"] == "req_joint_advisory" for item in seen)
        )


class QualityEvaluationTests(unittest.TestCase):
    def test_manual_quality_evaluator_reports_repeat_and_difficulty(self) -> None:
        items = assignments()
        repeated = dict(items[1])
        repeated["id"] = "req_7a_math__1"
        repeated["occurrence_index"] = 1
        repeated["slot"] = {"day_id": "mon", "period_id": "p3"}
        repeated["occupied_period_ids"] = ["p3"]
        report = evaluate_quality(DEMO, items + [repeated])
        ids = {item["constraint_id"] for item in report["violations"]}
        self.assertIn("SC-005", ids)
        self.assertEqual(
            report["total_penalty"],
            sum(item["weighted_penalty"] for item in report["violations"]),
        )
