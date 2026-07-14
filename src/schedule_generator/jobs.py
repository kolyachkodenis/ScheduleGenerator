"""Persistent generation-job workflow for the scheduling application."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Iterable, Mapping

from schedule_generator.api import (
    GenerationOptions,
    GenerationResult,
    SchedulingProblem,
    generate_schedule,
)
from schedule_generator.storage import DatasetStore, StoredDataset


class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class GenerationRequest:
    dataset_id: str
    dataset_revision: int | None = None
    alternatives: int = 1
    time_limit_seconds: float = 10.0
    seed: int = 1
    workers: int = 1

    def __post_init__(self) -> None:
        if not self.dataset_id:
            raise ValueError("dataset_id must not be empty")
        if self.dataset_revision is not None and self.dataset_revision < 1:
            raise ValueError("dataset_revision must be positive")
        if not 1 <= self.alternatives <= 10:
            raise ValueError("alternatives must be between 1 and 10")
        GenerationOptions(self.time_limit_seconds, self.seed, self.workers)


@dataclass(frozen=True)
class GenerationAlternative:
    index: int
    seed: int
    status: str
    quality_penalty: int | None
    result: dict[str, Any]


@dataclass(frozen=True)
class GenerationJob:
    job_id: str
    dataset_id: str
    dataset_revision: int
    dataset_fingerprint: str
    status: JobStatus
    parameters: dict[str, Any]
    progress_completed: int
    progress_total: int
    cancellation_requested: bool
    best_alternative: int | None
    result: dict[str, Any] | None
    diagnostics: tuple[dict[str, Any], ...]
    alternatives: tuple[GenerationAlternative, ...]


Generator = Callable[[SchedulingProblem, GenerationOptions], GenerationResult]
AssignmentValidator = Callable[[dict[str, Any], list[dict[str, Any]]], list[str]]


def _default_assignment_validator(
    dataset: dict[str, Any], assignments: list[dict[str, Any]]
) -> list[str]:
    from schedule_generator.prototype import verify_solution

    return verify_solution(dataset, assignments)


class SchedulingService:
    """Application API for school data, generation jobs, and validation."""

    def __init__(
        self,
        store: DatasetStore,
        generator: Generator = generate_schedule,
        assignment_validator: AssignmentValidator = _default_assignment_validator,
    ) -> None:
        self.store = store
        self.generator = generator
        self.assignment_validator = assignment_validator

    def get_reference_data(
        self, dataset_id: str, revision: int | None = None
    ) -> StoredDataset:
        return self.store.get(dataset_id, revision)

    def save_reference_data(self, dataset: Mapping[str, Any]) -> StoredDataset:
        return self.store.save(dataset)

    def replace_reference_collection(
        self, dataset_id: str, collection: str, records: Iterable[Mapping[str, Any]]
    ) -> StoredDataset:
        return self.store.replace_collection(dataset_id, collection, records)

    def create_job(self, request: GenerationRequest) -> GenerationJob:
        dataset = self.store.get(request.dataset_id, request.dataset_revision)
        job_id = uuid.uuid4().hex
        parameters = {
            "alternatives": request.alternatives,
            "time_limit_seconds": request.time_limit_seconds,
            "seed": request.seed,
            "workers": request.workers,
        }
        with self.store.connection:
            self.store.connection.execute(
                """
                INSERT INTO generation_jobs(
                    job_id, dataset_id, dataset_revision, dataset_fingerprint,
                    status, parameters_json, progress_total
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    dataset.dataset_id,
                    dataset.revision,
                    dataset.fingerprint,
                    JobStatus.PENDING.value,
                    json.dumps(parameters, sort_keys=True),
                    request.alternatives,
                ),
            )
        return self.get_job(job_id)

    def get_job(self, job_id: str) -> GenerationJob:
        row = self.store.connection.execute(
            "SELECT * FROM generation_jobs WHERE job_id = ?", (job_id,)
        ).fetchone()
        if row is None:
            raise KeyError(job_id)
        alternatives = self.store.connection.execute(
            "SELECT * FROM generation_alternatives WHERE job_id = ? "
            "ORDER BY alternative_index", (job_id,)
        ).fetchall()
        return GenerationJob(
            job_id=row["job_id"],
            dataset_id=row["dataset_id"],
            dataset_revision=int(row["dataset_revision"]),
            dataset_fingerprint=row["dataset_fingerprint"],
            status=JobStatus(row["status"]),
            parameters=json.loads(row["parameters_json"]),
            progress_completed=int(row["progress_completed"]),
            progress_total=int(row["progress_total"]),
            cancellation_requested=bool(row["cancellation_requested"]),
            best_alternative=row["best_alternative"],
            result=json.loads(row["result_json"]) if row["result_json"] else None,
            diagnostics=tuple(json.loads(row["diagnostics_json"])),
            alternatives=tuple(
                GenerationAlternative(
                    index=int(item["alternative_index"]),
                    seed=int(item["seed"]),
                    status=item["status"],
                    quality_penalty=item["quality_penalty"],
                    result=json.loads(item["result_json"]),
                )
                for item in alternatives
            ),
        )

    def list_jobs(self, dataset_id: str | None = None) -> list[GenerationJob]:
        if dataset_id is None:
            rows = self.store.connection.execute(
                "SELECT job_id FROM generation_jobs ORDER BY created_at, job_id"
            ).fetchall()
        else:
            rows = self.store.connection.execute(
                "SELECT job_id FROM generation_jobs WHERE dataset_id = ? "
                "ORDER BY created_at, job_id", (dataset_id,)
            ).fetchall()
        return [self.get_job(row[0]) for row in rows]

    def cancel_job(self, job_id: str) -> GenerationJob:
        job = self.get_job(job_id)
        if job.status in {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED}:
            return job
        with self.store.connection:
            if job.status is JobStatus.PENDING:
                updated = self.store.connection.execute(
                    "UPDATE generation_jobs SET cancellation_requested = 1, "
                    "status = ?, finished_at = CURRENT_TIMESTAMP "
                    "WHERE job_id = ? AND status = ?",
                    (
                        JobStatus.CANCELLED.value,
                        job_id,
                        JobStatus.PENDING.value,
                    ),
                )
            else:
                updated = self.store.connection.execute(
                    "UPDATE generation_jobs SET cancellation_requested = 1 "
                    "WHERE job_id = ? AND status = ?",
                    (job_id, JobStatus.RUNNING.value),
                )
        if updated.rowcount == 0:
            return self.cancel_job(job_id)
        return self.get_job(job_id)

    def run_job(self, job_id: str) -> GenerationJob:
        job = self.get_job(job_id)
        if job.status is not JobStatus.PENDING:
            raise ValueError(f"job {job_id} is not pending")
        with self.store.connection:
            claimed = self.store.connection.execute(
                "UPDATE generation_jobs SET status = ?, started_at = CURRENT_TIMESTAMP "
                "WHERE job_id = ? AND status = ?",
                (JobStatus.RUNNING.value, job_id, JobStatus.PENDING.value),
            )
        if claimed.rowcount != 1:
            raise ValueError(f"job {job_id} could not be claimed")
        try:
            dataset = self.store.get(job.dataset_id, job.dataset_revision)
            problem = SchedulingProblem.from_mapping(dataset.data)
            successful: list[tuple[int, int, dict[str, Any]]] = []
            for index in range(job.progress_total):
                if self.get_job(job_id).cancellation_requested:
                    return self._finish_cancelled(job_id)
                seed = int(job.parameters["seed"]) + index
                result = self.generator(
                    problem,
                    GenerationOptions(
                        time_limit_seconds=float(job.parameters["time_limit_seconds"]),
                        seed=seed,
                        workers=int(job.parameters["workers"]),
                    ),
                )
                payload = result.to_dict()
                penalty = (
                    result.quality.total_penalty
                    if result.is_success and result.quality is not None
                    else None
                )
                with self.store.connection:
                    self.store.connection.execute(
                        "INSERT INTO generation_alternatives(job_id, "
                        "alternative_index, seed, status, quality_penalty, result_json) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        (
                            job_id,
                            index,
                            seed,
                            result.status.value,
                            penalty,
                            json.dumps(payload, sort_keys=True),
                        ),
                    )
                    self.store.connection.execute(
                        "UPDATE generation_jobs SET progress_completed = ? WHERE job_id = ?",
                        (index + 1, job_id),
                    )
                if result.is_success:
                    successful.append((penalty or 0, index, payload))
                if self.get_job(job_id).cancellation_requested:
                    return self._finish_cancelled(job_id)
            if not successful:
                diagnostics = [
                    item
                    for alternative in self.get_job(job_id).alternatives
                    for item in (
                        alternative.result.get("diagnostics", [])
                        + [
                            {"code": "INVALID_RESULT", "message": message}
                            for message in alternative.result.get(
                                "validation_errors", []
                            )
                        ]
                    )
                ]
                return self._finish(job_id, JobStatus.FAILED, None, None, diagnostics)
            _, best_index, best_payload = min(successful)
            return self._finish(job_id, JobStatus.SUCCEEDED, best_index, best_payload, [])
        except Exception as error:
            if self.get_job(job_id).cancellation_requested:
                return self._finish_cancelled(job_id)
            return self._finish(
                job_id,
                JobStatus.FAILED,
                None,
                None,
                [{"code": "GENERATION_ERROR", "message": str(error)}],
            )

    def _finish_cancelled(self, job_id: str) -> GenerationJob:
        return self._finish(
            job_id,
            JobStatus.CANCELLED,
            None,
            None,
            [{"code": "CANCELLED", "message": "Generation was cancelled."}],
        )

    def _finish(
        self,
        job_id: str,
        status: JobStatus,
        best_alternative: int | None,
        result: dict[str, Any] | None,
        diagnostics: list[dict[str, Any]],
    ) -> GenerationJob:
        with self.store.connection:
            self.store.connection.execute(
                """
                UPDATE generation_jobs SET status = ?, best_alternative = ?,
                    result_json = ?, diagnostics_json = ?, finished_at = CURRENT_TIMESTAMP
                WHERE job_id = ?
                """,
                (
                    status.value,
                    best_alternative,
                    json.dumps(result, sort_keys=True) if result is not None else None,
                    json.dumps(diagnostics, sort_keys=True),
                    job_id,
                ),
            )
        return self.get_job(job_id)

    def validate_assignments(
        self,
        dataset_id: str,
        assignments: list[dict[str, Any]],
        revision: int | None = None,
    ) -> list[str]:
        dataset = self.store.get(dataset_id, revision)
        return self.assignment_validator(dataset.data, assignments)
