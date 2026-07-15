from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from pypdf import PdfReader

from schedule_generator.api import GenerationOptions, GenerationResult, SchedulingProblem
from schedule_generator.editing import TimetableEditingService
from schedule_generator.jobs import GenerationRequest, SchedulingService
from schedule_generator.publication import PublicationService
from schedule_generator.storage import DatasetStore


ROOT = Path(__file__).resolve().parents[1]
DEMO = json.loads((ROOT / "examples" / "small-school.json").read_text(encoding="utf-8"))


def result_for(problem: SchedulingProblem, _options: GenerationOptions) -> GenerationResult:
    return GenerationResult.from_backend(
        problem,
        {
            "status": "FEASIBLE",
            "assignments": [
                {
                    "id": "req_joint_advisory__0",
                    "requirement_id": "req_joint_advisory",
                    "occurrence_index": 0,
                    "slot": {"day_id": "mon", "period_id": "p1"},
                    "occupied_period_ids": ["p1"],
                    "teacher_id": "t_art",
                    "classroom_id": "room_7a",
                }
            ],
            "quality_report": {"total_penalty": 0, "by_constraint": {}, "violations": []},
            "diagnostics": [],
            "validation_errors": [],
        },
    )


class PublicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.store = DatasetStore(root / "school.db")
        self.store.save(DEMO)
        jobs = SchedulingService(self.store, result_for)
        job = jobs.run_job(jobs.create_job(GenerationRequest(DEMO["dataset_id"])).job_id)
        self.editing = TimetableEditingService(
            self.store,
            validator=lambda _dataset, _assignments: [],
            quality_evaluator=lambda _dataset, _assignments: {
                "total_penalty": 0,
                "by_constraint": {},
                "violations": [],
            },
            generator=result_for,
        )
        self.draft = self.editing.create_from_job(job.job_id)
        self.publications = PublicationService(self.store, root / "published")

    def tearDown(self) -> None:
        self.store.close()
        self.temporary.cleanup()

    def test_approved_version_exports_class_and_teacher_views(self) -> None:
        approved = self.publications.approve(self.draft.draft_id)
        self.assertEqual(approved.status, "APPROVED")
        published = self.publications.publish(approved.publication_id)
        self.assertEqual(published.status, "PUBLISHED")
        self.assertEqual(set(published.artifacts), {"xlsx", "pdf"})

        xlsx, content_type = self.publications.download(
            published.artifacts["xlsx"]["filename"]
        )
        self.assertIn("spreadsheet", content_type)
        with zipfile.ZipFile(xlsx) as archive:
            workbook = archive.read("xl/workbook.xml").decode()
        self.assertIn("Class - Class 7A", workbook)
        self.assertIn("Teacher -", workbook)

        pdf, content_type = self.publications.download(
            published.artifacts["pdf"]["filename"]
        )
        self.assertEqual(content_type, "application/pdf")
        self.assertEqual(len(PdfReader(pdf).pages), len(DEMO["classes"]) + len(DEMO["teachers"]))

    def test_unpublished_artifacts_are_not_downloadable(self) -> None:
        published = self.publications.publish(
            self.publications.approve(self.draft.draft_id).publication_id
        )
        filename = published.artifacts["pdf"]["filename"]
        unpublished = self.publications.unpublish(published.publication_id)
        self.assertEqual(unpublished.status, "UNPUBLISHED")
        with self.assertRaises(KeyError):
            self.publications.download(filename)

    def test_conflicted_draft_cannot_be_approved(self) -> None:
        self.store.connection.execute(
            "UPDATE timetable_draft_versions SET validation_errors_json = ? "
            "WHERE draft_id = ? AND version = 0",
            (json.dumps(["teacher collision"]), self.draft.draft_id),
        )
        with self.assertRaisesRegex(ValueError, "validation errors"):
            self.publications.approve(self.draft.draft_id)

    def test_approval_remains_pinned_after_further_editing(self) -> None:
        approved = self.publications.approve(self.draft.draft_id)
        self.editing.move(
            self.draft.draft_id, "req_joint_advisory__0", "tue", "p2"
        )
        published = self.publications.publish(approved.publication_id)
        self.assertEqual(published.version, 0)
