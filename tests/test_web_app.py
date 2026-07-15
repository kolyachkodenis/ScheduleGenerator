from __future__ import annotations

import base64
import json
import tempfile
import unittest
from http import HTTPStatus
from pathlib import Path

from schedule_generator.api import GenerationOptions, GenerationResult, SchedulingProblem
from schedule_generator.editing import TimetableEditingService
from schedule_generator.jobs import SchedulingService
from schedule_generator.web import WebApplication


def successful_result(
    problem: SchedulingProblem, options: GenerationOptions
) -> GenerationResult:
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


def editing_factory(store):
    return TimetableEditingService(
        store,
        validator=lambda _dataset, _assignments: [],
        quality_evaluator=lambda _dataset, _assignments: {
            "total_penalty": 0,
            "by_constraint": {},
            "violations": [],
        },
        generator=successful_result,
    )


class WebApplicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.application = WebApplication(
            Path(self.temporary.name) / "school.db",
            run_in_background=False,
            service_factory=service_factory,
            editing_factory=editing_factory,
        )
        original_dispatch = self.application.dispatch
        bootstrap = original_dispatch(
            "POST",
            "/api/security/bootstrap",
            json.dumps(
                {"username": "admin", "password": "Long-Initial-Password!42"}
            ).encode(),
        )
        cookie = dict(bootstrap.headers)["Set-Cookie"].split(";", 1)[0]
        self.raw_dispatch = original_dispatch
        self.application.dispatch = lambda method, path, body=b"": original_dispatch(
            method, path, body, {"Cookie": cookie}
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def payload(response) -> dict:
        return json.loads(response.body)

    def test_static_operator_interface_is_served(self) -> None:
        page = self.application.dispatch("GET", "/")
        script = self.application.dispatch("GET", "/assets/app.js")
        translations = self.application.dispatch("GET", "/assets/i18n.js")
        style = self.application.dispatch("GET", "/assets/styles.css")
        self.assertEqual(page.status, HTTPStatus.OK)
        self.assertIn(b"School data", page.body)
        self.assertIn(b"startGeneration", script.body)
        self.assertEqual(translations.status, HTTPStatus.OK)
        self.assertIn("Составить расписание".encode(), translations.body)
        self.assertIn("Понедельник".encode(), translations.body)
        self.assertIn("Математика".encode(), translations.body)
        self.assertIn("7-й урок".encode(), translations.body)
        self.assertIn(b"schedule-generator-language", translations.body)
        self.assertIn(b"dataLabel(day.label)", script.body)
        self.assertIn(b"dataLabel(subject.label)", script.body)
        self.assertIn(b"job.dataset_revision === state.dataset?.revision", script.body)
        self.assertIn(b'data-language="ru"', page.body)
        self.assertNotIn(b"collection-json", page.body)
        self.assertNotIn(b"collection-json", script.body)
        self.assertIn(b"visual-editor", page.body)
        self.assertIn(b"saveConfiguration", script.body)
        self.assertIn(b"configuration-file", page.body)
        self.assertIn(b"quality-panel", page.body)
        self.assertIn(b"data-subject-difficulty", script.body)
        self.assertIn(b".assignment-choice[hidden]", style.body)
        self.assertIn(b"top: 72px", style.body)
        self.assertIn(b"z-index: 120", style.body)
        self.assertIn(b"route not found", translations.body)
        self.assertIn(b".timetable", style.body)

    def test_authentication_and_role_authorization(self) -> None:
        unauthenticated = self.raw_dispatch("GET", "/api/state")
        self.assertEqual(unauthenticated.status, HTTPStatus.UNAUTHORIZED)
        created = self.application.dispatch(
            "POST",
            "/api/users",
            json.dumps(
                {
                    "username": "reader",
                    "password": "Distinct-Viewing-Key!42",
                    "role": "reader",
                }
            ).encode(),
        )
        self.assertEqual(created.status, HTTPStatus.CREATED)
        login = self.raw_dispatch(
            "POST",
            "/api/security/login",
            json.dumps(
                {"username": "reader", "password": "Distinct-Viewing-Key!42"}
            ).encode(),
        )
        reader_cookie = dict(login.headers)["Set-Cookie"].split(";", 1)[0]
        readable = self.raw_dispatch("GET", "/api/state", headers={"Cookie": reader_cookie})
        forbidden = self.raw_dispatch("POST", "/api/demo", headers={"Cookie": reader_cookie})
        self.assertEqual(readable.status, HTTPStatus.OK)
        self.assertEqual(forbidden.status, HTTPStatus.FORBIDDEN)

    def test_health_and_protected_metrics_endpoints(self) -> None:
        live = self.raw_dispatch("GET", "/health/live")
        ready = self.raw_dispatch("GET", "/health/ready")
        protected = WebApplication(
            Path(self.temporary.name) / "metrics.db", metrics_token="monitoring-secret"
        )
        denied = protected.dispatch("GET", "/metrics")
        metrics = protected.dispatch(
            "GET",
            "/metrics",
            headers={"Authorization": "Bearer monitoring-secret"},
        )
        self.assertEqual(live.status, HTTPStatus.OK)
        self.assertEqual(ready.status, HTTPStatus.OK)
        self.assertEqual(self.payload(ready)["checks"]["database"], "ok")
        self.assertEqual(denied.status, HTTPStatus.UNAUTHORIZED)
        self.assertEqual(metrics.status, HTTPStatus.OK)
        self.assertIn(b"schedule_generator_up 1", metrics.body)

    def test_admin_routes_create_backup_and_expose_audit(self) -> None:
        self.application.dispatch("POST", "/api/demo")
        backup = self.application.dispatch("POST", "/api/admin/backup")
        audit = self.payload(self.application.dispatch("GET", "/api/audit"))
        self.assertEqual(backup.status, HTTPStatus.CREATED)
        self.assertTrue(any(item["action"] == "backup.created" for item in audit["events"]))

    def test_demo_setup_and_state_endpoint(self) -> None:
        created = self.application.dispatch("POST", "/api/demo")
        self.assertEqual(created.status, HTTPStatus.CREATED)
        state = self.payload(self.application.dispatch("GET", "/api/state"))
        self.assertEqual(len(state["datasets"]), 1)
        self.assertEqual(state["datasets"][0]["dataset_id"], "small_school_demo")
        self.assertEqual(state["datasets"][0]["data"]["classes"][0]["id"], "class_5a")
        periods = state["datasets"][0]["data"]["academic_period"]["periods"]
        self.assertEqual(periods[-1]["id"], "p7")
        self.assertEqual(periods[-1]["ordinal"], 7)

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

    def test_related_configuration_is_saved_atomically(self) -> None:
        self.application.dispatch("POST", "/api/demo")
        state = self.payload(self.application.dispatch("GET", "/api/state"))
        data = state["datasets"][0]["data"]
        teachers = data["teachers"]
        teachers[0]["classroom_id"] = "room_5a"
        first_requirement = data["curriculum_requirements"][0]
        removed_teacher_id = first_requirement["eligible_teacher_ids"][0]
        first_requirement["eligible_teacher_ids"] = first_requirement[
            "eligible_teacher_ids"
        ][1:]
        response = self.application.dispatch(
            "PUT",
            "/api/datasets/small_school_demo/configuration",
            json.dumps(
                {
                    "updates": {
                        "teachers": teachers,
                        "curriculum_requirements": data["curriculum_requirements"],
                    }
                }
            ).encode(),
        )
        self.assertEqual(response.status, HTTPStatus.OK)
        self.assertEqual(self.payload(response)["revision"], 2)
        updated = self.payload(self.application.dispatch("GET", "/api/state"))
        self.assertEqual(
            updated["datasets"][0]["data"]["teachers"][0]["classroom_id"],
            "room_5a",
        )
        self.assertNotIn(
            removed_teacher_id,
            updated["datasets"][0]["data"]["curriculum_requirements"][0][
                "eligible_teacher_ids"
            ],
        )

    def test_configuration_workbook_can_be_exported_and_imported(self) -> None:
        self.application.dispatch("POST", "/api/demo")
        exported = self.application.dispatch(
            "GET", "/api/datasets/small_school_demo/configuration-workbook"
        )
        self.assertEqual(exported.status, HTTPStatus.OK)
        self.assertEqual(exported.body[:2], b"PK")
        imported = self.application.dispatch(
            "POST",
            "/api/datasets/small_school_demo/configuration-workbook",
            json.dumps(
                {"content_base64": base64.b64encode(exported.body).decode("ascii")}
            ).encode(),
        )
        self.assertEqual(imported.status, HTTPStatus.OK)
        self.assertEqual(self.payload(imported)["revision"], 2)

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

    def test_draft_routes_support_move_lock_undo_and_compare(self) -> None:
        self.application.dispatch("POST", "/api/demo")
        job = self.payload(
            self.application.dispatch(
                "POST",
                "/api/jobs",
                json.dumps({"dataset_id": "small_school_demo"}).encode(),
            )
        )
        draft = self.payload(
            self.application.dispatch("POST", f"/api/jobs/{job['job_id']}/draft")
        )
        moved = self.payload(
            self.application.dispatch(
                "POST",
                f"/api/drafts/{draft['draft_id']}/move",
                json.dumps(
                    {
                        "assignment_id": "req_joint_advisory__0",
                        "day_id": "tue",
                        "period_id": "p2",
                    }
                ).encode(),
            )
        )
        self.assertEqual(moved["current_version"], 1)
        locked = self.payload(
            self.application.dispatch(
                "POST",
                f"/api/drafts/{draft['draft_id']}/lock",
                json.dumps(
                    {"assignment_id": "req_joint_advisory__0", "locked": True}
                ).encode(),
            )
        )
        self.assertEqual(locked["locked_assignment_ids"], ["req_joint_advisory__0"])
        comparison = self.payload(
            self.application.dispatch(
                "POST",
                f"/api/drafts/{draft['draft_id']}/compare",
                json.dumps({"left": 0, "right": 1}).encode(),
            )
        )
        self.assertEqual(len(comparison["changes"]), 1)
        undone = self.payload(
            self.application.dispatch(
                "POST", f"/api/drafts/{draft['draft_id']}/undo"
            )
        )
        self.assertEqual(undone["current_version"], 0)

    def test_approved_timetable_can_be_published_downloaded_and_unpublished(self) -> None:
        self.application.dispatch("POST", "/api/demo")
        job = self.payload(
            self.application.dispatch(
                "POST",
                "/api/jobs",
                json.dumps({"dataset_id": "small_school_demo"}).encode(),
            )
        )
        draft = self.payload(
            self.application.dispatch("POST", f"/api/jobs/{job['job_id']}/draft")
        )
        approved = self.payload(
            self.application.dispatch(
                "POST", f"/api/drafts/{draft['draft_id']}/approve"
            )
        )
        self.assertEqual(approved["status"], "APPROVED")
        published = self.payload(
            self.application.dispatch(
                "POST", f"/api/publications/{approved['publication_id']}/publish"
            )
        )
        pdf = published["artifacts"]["pdf"]["filename"]
        download = self.application.dispatch("GET", f"/downloads/{pdf}")
        self.assertEqual(download.status, HTTPStatus.OK)
        self.assertEqual(download.content_type, "application/pdf")
        self.assertTrue(download.body.startswith(b"%PDF"))
        unpublished = self.payload(
            self.application.dispatch(
                "POST", f"/api/publications/{approved['publication_id']}/unpublish"
            )
        )
        self.assertEqual(unpublished["status"], "UNPUBLISHED")
        self.assertNotEqual(self.application.dispatch("GET", f"/downloads/{pdf}").status, HTTPStatus.OK)

    def test_bad_json_and_unknown_routes_are_reported(self) -> None:
        malformed = self.application.dispatch("POST", "/api/jobs", b"{")
        wrong_shape = self.application.dispatch("POST", "/api/jobs", b"[]")
        missing = self.application.dispatch("GET", "/api/unknown")
        self.assertEqual(malformed.status, HTTPStatus.BAD_REQUEST)
        self.assertEqual(wrong_shape.status, HTTPStatus.BAD_REQUEST)
        self.assertEqual(missing.status, HTTPStatus.NOT_FOUND)
