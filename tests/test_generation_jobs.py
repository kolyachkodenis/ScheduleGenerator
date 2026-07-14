from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from schedule_generator.api import GenerationOptions, GenerationResult, SchedulingProblem
from schedule_generator.jobs import GenerationRequest, JobStatus, SchedulingService
from schedule_generator.storage import DatasetStore


ROOT = Path(__file__).resolve().parents[1]
DEMO = json.loads((ROOT / "examples" / "small-school.json").read_text(encoding="utf-8"))


def successful_result(
    problem: SchedulingProblem, options: GenerationOptions
) -> GenerationResult:
    penalty = 100 - options.seed
    return GenerationResult.from_backend(
        problem,
        {
            "status": "FEASIBLE",
            "assignments": [],
            "quality_report": {
                "total_penalty": penalty,
                "by_constraint": {
                    "SC-001": {"raw": penalty, "weighted": penalty}
                },
                "violations": [],
            },
            "diagnostics": [],
            "validation_errors": [],
        },
    )


class GenerationJobTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.store = DatasetStore(Path(self.temporary.name) / "school.db")
        self.stored = self.store.save(DEMO)

    def tearDown(self) -> None:
        self.store.close()
        self.temporary.cleanup()

    def test_job_pins_dataset_revision_and_keeps_ranked_alternatives(self) -> None:
        service = SchedulingService(self.store, successful_result)
        job = service.create_job(
            GenerationRequest(DEMO["dataset_id"], alternatives=3, seed=5)
        )
        changed = copy.deepcopy(DEMO)
        changed["school"]["label"] = "Later revision"
        self.store.save(changed)

        completed = service.run_job(job.job_id)

        self.assertEqual(completed.status, JobStatus.SUCCEEDED)
        self.assertEqual(completed.dataset_revision, 1)
        self.assertEqual(completed.dataset_fingerprint, self.stored.fingerprint)
        self.assertEqual(completed.progress_completed, 3)
        self.assertEqual([item.seed for item in completed.alternatives], [5, 6, 7])
        self.assertEqual(completed.best_alternative, 2)
        self.assertEqual(completed.result["quality_report"]["total_penalty"], 93)

    def test_pending_job_can_be_cancelled_without_running_solver(self) -> None:
        service = SchedulingService(self.store, successful_result)
        job = service.create_job(GenerationRequest(DEMO["dataset_id"]))
        cancelled = service.cancel_job(job.job_id)
        self.assertEqual(cancelled.status, JobStatus.CANCELLED)
        with self.assertRaisesRegex(ValueError, "is not pending"):
            service.run_job(job.job_id)

    def test_running_job_observes_cancellation_between_alternatives(self) -> None:
        holder: dict[str, object] = {}

        def cancelling_generator(
            problem: SchedulingProblem, options: GenerationOptions
        ) -> GenerationResult:
            service = holder["service"]
            service.cancel_job(holder["job_id"])
            return successful_result(problem, options)

        service = SchedulingService(self.store, cancelling_generator)
        holder["service"] = service
        job = service.create_job(
            GenerationRequest(DEMO["dataset_id"], alternatives=3)
        )
        holder["job_id"] = job.job_id

        cancelled = service.run_job(job.job_id)

        self.assertEqual(cancelled.status, JobStatus.CANCELLED)
        self.assertEqual(cancelled.progress_completed, 1)
        self.assertEqual(len(cancelled.alternatives), 1)

    def test_generation_failure_is_persisted_as_diagnostic(self) -> None:
        def broken_generator(
            _problem: SchedulingProblem, _options: GenerationOptions
        ) -> GenerationResult:
            raise RuntimeError("solver process failed")

        service = SchedulingService(self.store, broken_generator)
        job = service.create_job(GenerationRequest(DEMO["dataset_id"]))
        failed = service.run_job(job.job_id)
        self.assertEqual(failed.status, JobStatus.FAILED)
        self.assertEqual(failed.diagnostics[0]["code"], "GENERATION_ERROR")
        self.assertIn("solver process failed", failed.diagnostics[0]["message"])

    def test_manual_assignment_validation_uses_pinned_dataset(self) -> None:
        seen: list[str] = []

        def validator(dataset: dict, assignments: list[dict]) -> list[str]:
            seen.append(dataset["dataset_id"])
            return [] if assignments else ["no assignments"]

        service = SchedulingService(
            self.store, successful_result, assignment_validator=validator
        )
        errors = service.validate_assignments(
            DEMO["dataset_id"], [{"id": "manual"}], revision=1
        )
        self.assertEqual(errors, [])
        self.assertEqual(seen, [DEMO["dataset_id"]])

    def test_jobs_can_be_listed_by_dataset(self) -> None:
        service = SchedulingService(self.store, successful_result)
        first = service.create_job(GenerationRequest(DEMO["dataset_id"]))
        second = service.create_job(GenerationRequest(DEMO["dataset_id"]))
        self.assertEqual(
            {job.job_id for job in service.list_jobs(DEMO["dataset_id"])},
            {first.job_id, second.job_id},
        )
