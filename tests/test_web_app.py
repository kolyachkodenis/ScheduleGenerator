from __future__ import annotations

import json
import tempfile
import unittest
from http import HTTPStatus
from pathlib import Path

from schedule_generator.api import GenerationOptions, GenerationResult, SchedulingProblem
from schedule_generator.jobs import SchedulingService
from schedule_generator.web import WebApplication


def successful_result(
    problem: SchedulingProblem, options: GenerationOptions
) -> GenerationResult:
    return GenerationResult.from_backend(
        problem,
        {
            "status": "FEASIBLE",
            "assignments": [],
            "quality_report": {
                "total_penalty": options.seed,
                "by_constraint": {},
                "violations": [],
            },
            "diagnostics": [],
            "validation_errors": [],
        },
    )


def service_factory(store):
    return SchedulingService(
        store,
        successful_result,
        assignment_validator=lambda _dataset, assignments: [] if assignments else [
            "no assignments"
        ],
    )


class WebApplicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.application = WebApplication(
            Path(self.temporary.name) / "school.db",
            run_in_background=False,
            service_factory=service_factory,
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def payload(response) -> dict:
        return json.loads(response.body)

    def test_static_operator_interface_is_served(self) -> None:
        page = self.application.dispatch("GET", "/")
        script = self.application.dispatch("GET", "/assets/app.js")
        style = self.application.dispatch("GET", "/assets/styles.css")
        self.assertEqual(page.status, HTTPStatus.OK)
        self.assertIn(b"School data", page.body)
        self.assertIn(b"startGeneration", script.body)
        self.assertIn(b".timetable", style.body)

    def test_demo_setup_and_state_endpoint(self) -> None:
        created = self.application.dispatch("POST", "/api/demo")
        self.assertEqual(created.status, HTTPStatus.CREATED)
        state = self.payload(self.application.dispatch("GET", "/api/state"))
        self.assertEqual(len(state["datasets"]), 1)
        self.assertEqual(state["datasets"][0]["dataset_id"], "small_school_demo")
        self.assertEqual(state["datasets"][0]["data"]["classes"][0]["id"], "class_7a")

    def test_collection_edit_creates_validated_revision(self) -> None:
        self.application.dispatch("POST", "/api/demo")
        state = self.payload(self.application.dispatch("GET", "/api/state"))
        classes = state["datasets"][0]["data"]["classes"]
        classes[0]["label"] = "Edited Class 7A"
        response = self.application.dispatch(
            "PUT",
            "/api/datasets/small_school_demo/collections/classes",
            json.dumps({"records": classes}).encode(),
        )
        self.assertEqual(response.status, HTTPStatus.OK)
        self.assertEqual(self.payload(response)["revision"], 2)

    def test_generation_route_returns_completed_job_and_result(self) -> None:
        self.application.dispatch("POST", "/api/demo")
        response = self.application.dispatch(
            "POST",
            "/api/jobs",
            json.dumps(
                {
                    "dataset_id": "small_school_demo",
                    "alternatives": 2,
                    "time_limit_seconds": 3,
                    "seed": 4,
                }
            ).encode(),
        )
        payload = self.payload(response)
        self.assertEqual(response.status, HTTPStatus.CREATED)
        self.assertEqual(payload["status"], "SUCCEEDED")
        self.assertEqual(payload["progress"], {"completed": 2, "total": 2})
        self.assertEqual(len(payload["alternatives"]), 2)
        self.assertIsNotNone(payload["result"])

    def test_manual_validation_route_returns_actionable_errors(self) -> None:
        self.application.dispatch("POST", "/api/demo")
        invalid = self.application.dispatch(
            "POST",
            "/api/validate",
            json.dumps(
                {"dataset_id": "small_school_demo", "assignments": []}
            ).encode(),
        )
        self.assertEqual(
            self.payload(invalid), {"valid": False, "errors": ["no assignments"]}
        )

    def test_bad_json_and_unknown_routes_are_reported(self) -> None:
        malformed = self.application.dispatch("POST", "/api/jobs", b"{")
        wrong_shape = self.application.dispatch("POST", "/api/jobs", b"[]")
        missing = self.application.dispatch("GET", "/api/unknown")
        self.assertEqual(malformed.status, HTTPStatus.BAD_REQUEST)
        self.assertEqual(wrong_shape.status, HTTPStatus.BAD_REQUEST)
        self.assertEqual(missing.status, HTTPStatus.NOT_FOUND)
