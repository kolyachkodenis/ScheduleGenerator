"""Small local HTTP application for the first operator interface."""

from __future__ import annotations

import argparse
import json
import mimetypes
import threading
from dataclasses import asdict, dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import unquote, urlparse

from schedule_generator.api import GenerationOptions
from schedule_generator.editing import TimetableDraft, TimetableEditingService
from schedule_generator.jobs import GenerationJob, GenerationRequest, SchedulingService
from schedule_generator.storage import DatasetStore


ASSET_ROOT = Path(__file__).with_name("web")
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEMO_PATH = PROJECT_ROOT / "examples" / "small-school.json"


@dataclass(frozen=True)
class WebResponse:
    status: int
    body: bytes
    content_type: str = "application/json; charset=utf-8"

    @classmethod
    def json(cls, status: int, value: Any) -> WebResponse:
        return cls(
            status,
            (json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n").encode(
                "utf-8"
            ),
        )


def job_to_dict(job: GenerationJob) -> dict[str, Any]:
    return {
        "job_id": job.job_id,
        "dataset_id": job.dataset_id,
        "dataset_revision": job.dataset_revision,
        "dataset_fingerprint": job.dataset_fingerprint,
        "status": job.status.value,
        "parameters": job.parameters,
        "progress": {
            "completed": job.progress_completed,
            "total": job.progress_total,
        },
        "cancellation_requested": job.cancellation_requested,
        "best_alternative": job.best_alternative,
        "result": job.result,
        "diagnostics": list(job.diagnostics),
        "alternatives": [asdict(item) for item in job.alternatives],
    }


def draft_to_dict(draft: TimetableDraft) -> dict[str, Any]:
    return {
        "draft_id": draft.draft_id,
        "job_id": draft.job_id,
        "dataset_id": draft.dataset_id,
        "dataset_revision": draft.dataset_revision,
        "current_version": draft.current_version,
        "latest_version": draft.latest_version,
        "locked_assignment_ids": list(draft.locked_assignment_ids),
        "version": asdict(draft.version),
        "history": list(draft.history),
    }


class WebApplication:
    """Route requests without coupling behavior to the HTTP server implementation."""

    def __init__(
        self,
        database: str | Path,
        run_in_background: bool = True,
        service_factory: Callable[[DatasetStore], SchedulingService] = SchedulingService,
        editing_factory: Callable[[DatasetStore], TimetableEditingService] = TimetableEditingService,
    ) -> None:
        self.database = Path(database)
        self.run_in_background = run_in_background
        self.service_factory = service_factory
        self.editing_factory = editing_factory

    def _service(self) -> tuple[DatasetStore, SchedulingService]:
        store = DatasetStore(self.database)
        return store, self.service_factory(store)

    def _editing(self) -> tuple[DatasetStore, TimetableEditingService]:
        store = DatasetStore(self.database)
        return store, self.editing_factory(store)

    def dispatch(self, method: str, raw_path: str, body: bytes = b"") -> WebResponse:
        path = unquote(urlparse(raw_path).path)
        try:
            if method == "GET" and path in {"/", "/index.html"}:
                return self._asset("index.html")
            if method == "GET" and path.startswith("/assets/"):
                return self._asset(path.removeprefix("/assets/"))
            payload = json.loads(body.decode("utf-8")) if body else {}
            if not isinstance(payload, dict):
                raise ValueError("request body must be a JSON object")
            if method == "GET" and path == "/api/state":
                return self._state()
            if method == "POST" and path == "/api/demo":
                return self._load_demo()
            if method == "POST" and path == "/api/jobs":
                return self._create_job(payload)
            if path.startswith("/api/jobs/"):
                job_id, action = self._job_path(path)
                if method == "GET" and action is None:
                    return self._get_job(job_id)
                if method == "POST" and action == "cancel":
                    return self._cancel_job(job_id)
                if method == "POST" and action == "draft":
                    return self._create_draft(job_id)
            if path.startswith("/api/drafts/"):
                draft_id, action = self._draft_path(path)
                if method == "GET" and action is None:
                    return self._get_draft(draft_id)
                if method == "POST":
                    return self._edit_draft(draft_id, action, payload)
            if method == "PUT" and path.startswith("/api/datasets/"):
                return self._replace_collection(path, payload)
            if method == "POST" and path == "/api/validate":
                return self._validate(payload)
            return WebResponse.json(HTTPStatus.NOT_FOUND, {"error": "route not found"})
        except (KeyError, ValueError, json.JSONDecodeError, UnicodeError) as error:
            return WebResponse.json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
        except Exception as error:
            return WebResponse.json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": "request failed", "detail": str(error)},
            )

    def _asset(self, name: str) -> WebResponse:
        assets = {
            "index.html": ASSET_ROOT / "index.html",
            "app.js": ASSET_ROOT / "app.js",
            "styles.css": ASSET_ROOT / "styles.css",
        }
        path = assets.get(name)
        if path is None or not path.is_file():
            return WebResponse.json(HTTPStatus.NOT_FOUND, {"error": "asset not found"})
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if content_type.startswith(("text/", "application/javascript")):
            content_type += "; charset=utf-8"
        return WebResponse(HTTPStatus.OK, path.read_bytes(), content_type)

    def _state(self) -> WebResponse:
        store, service = self._service()
        try:
            datasets = [
                {
                    "dataset_id": item.dataset_id,
                    "revision": item.revision,
                    "fingerprint": item.fingerprint,
                    "data": item.data,
                }
                for item in store.list()
            ]
            jobs = [job_to_dict(job) for job in service.list_jobs()]
            editing = self.editing_factory(store)
            drafts = [draft_to_dict(draft) for draft in editing.list()]
            return WebResponse.json(
                HTTPStatus.OK,
                {"datasets": datasets, "jobs": jobs, "drafts": drafts},
            )
        finally:
            store.close()

    def _load_demo(self) -> WebResponse:
        dataset = json.loads(DEMO_PATH.read_text(encoding="utf-8"))
        store, service = self._service()
        try:
            saved = service.save_reference_data(dataset)
            return WebResponse.json(
                HTTPStatus.CREATED,
                {"dataset_id": saved.dataset_id, "revision": saved.revision},
            )
        finally:
            store.close()

    def _replace_collection(
        self, path: str, payload: dict[str, Any]
    ) -> WebResponse:
        parts = path.strip("/").split("/")
        if len(parts) != 5 or parts[3] != "collections":
            raise ValueError("invalid collection route")
        dataset_id, collection = parts[2], parts[4]
        records = payload.get("records")
        if not isinstance(records, list):
            raise ValueError("records must be a list")
        store, service = self._service()
        try:
            saved = service.replace_reference_collection(dataset_id, collection, records)
            return WebResponse.json(
                HTTPStatus.OK,
                {"dataset_id": saved.dataset_id, "revision": saved.revision},
            )
        finally:
            store.close()

    def _create_job(self, payload: dict[str, Any]) -> WebResponse:
        request = GenerationRequest(
            dataset_id=str(payload.get("dataset_id", "")),
            alternatives=int(payload.get("alternatives", 1)),
            time_limit_seconds=float(payload.get("time_limit_seconds", 10)),
            seed=int(payload.get("seed", 1)),
            workers=int(payload.get("workers", 1)),
        )
        store, service = self._service()
        try:
            job = service.create_job(request)
        finally:
            store.close()
        if self.run_in_background:
            threading.Thread(
                target=self._run_job,
                args=(job.job_id,),
                daemon=True,
                name=f"schedule-job-{job.job_id[:8]}",
            ).start()
        else:
            self._run_job(job.job_id)
            return self._get_job(job.job_id, status=HTTPStatus.CREATED)
        return WebResponse.json(HTTPStatus.ACCEPTED, job_to_dict(job))

    def _run_job(self, job_id: str) -> None:
        store, service = self._service()
        try:
            service.run_job(job_id)
        finally:
            store.close()

    @staticmethod
    def _job_path(path: str) -> tuple[str, str | None]:
        parts = path.strip("/").split("/")
        if len(parts) not in {3, 4}:
            raise ValueError("invalid job route")
        return parts[2], parts[3] if len(parts) == 4 else None

    def _get_job(
        self, job_id: str, status: int = HTTPStatus.OK
    ) -> WebResponse:
        store, service = self._service()
        try:
            return WebResponse.json(status, job_to_dict(service.get_job(job_id)))
        finally:
            store.close()

    def _cancel_job(self, job_id: str) -> WebResponse:
        store, service = self._service()
        try:
            return WebResponse.json(
                HTTPStatus.OK, job_to_dict(service.cancel_job(job_id))
            )
        finally:
            store.close()

    @staticmethod
    def _draft_path(path: str) -> tuple[str, str | None]:
        parts = path.strip("/").split("/")
        if len(parts) not in {3, 4}:
            raise ValueError("invalid draft route")
        return parts[2], parts[3] if len(parts) == 4 else None

    def _create_draft(self, job_id: str) -> WebResponse:
        store, editing = self._editing()
        try:
            return WebResponse.json(
                HTTPStatus.CREATED, draft_to_dict(editing.create_from_job(job_id))
            )
        finally:
            store.close()

    def _get_draft(self, draft_id: str) -> WebResponse:
        store, editing = self._editing()
        try:
            return WebResponse.json(HTTPStatus.OK, draft_to_dict(editing.get(draft_id)))
        finally:
            store.close()

    def _edit_draft(
        self, draft_id: str, action: str | None, payload: dict[str, Any]
    ) -> WebResponse:
        store, editing = self._editing()
        try:
            if action == "move":
                draft = editing.move(
                    draft_id,
                    str(payload.get("assignment_id", "")),
                    str(payload.get("day_id", "")),
                    str(payload.get("period_id", "")),
                    payload.get("teacher_id"),
                    payload.get("classroom_id"),
                )
                return WebResponse.json(HTTPStatus.OK, draft_to_dict(draft))
            if action == "lock":
                draft = editing.set_lock(
                    draft_id,
                    str(payload.get("assignment_id", "")),
                    bool(payload.get("locked", True)),
                )
                return WebResponse.json(HTTPStatus.OK, draft_to_dict(draft))
            if action == "undo":
                return WebResponse.json(HTTPStatus.OK, draft_to_dict(editing.undo(draft_id)))
            if action == "redo":
                return WebResponse.json(HTTPStatus.OK, draft_to_dict(editing.redo(draft_id)))
            if action == "regenerate":
                options = GenerationOptions(
                    float(payload.get("time_limit_seconds", 10)),
                    int(payload.get("seed", 1)),
                    int(payload.get("workers", 1)),
                )
                return WebResponse.json(
                    HTTPStatus.OK,
                    draft_to_dict(editing.regenerate(draft_id, options)),
                )
            if action == "compare":
                return WebResponse.json(
                    HTTPStatus.OK,
                    editing.compare(
                        draft_id, int(payload.get("left", 0)), int(payload["right"])
                    ),
                )
            raise ValueError("unknown draft action")
        finally:
            store.close()

    def _validate(self, payload: dict[str, Any]) -> WebResponse:
        assignments = payload.get("assignments")
        if not isinstance(assignments, list):
            raise ValueError("assignments must be a list")
        store, service = self._service()
        try:
            errors = service.validate_assignments(
                str(payload.get("dataset_id", "")),
                assignments,
                payload.get("revision"),
            )
            return WebResponse.json(
                HTTPStatus.OK, {"valid": not errors, "errors": errors}
            )
        finally:
            store.close()


def make_handler(application: WebApplication) -> type[BaseHTTPRequestHandler]:
    class RequestHandler(BaseHTTPRequestHandler):
        def _respond(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 10_000_000:
                response = WebResponse.json(
                    HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "request too large"}
                )
            else:
                response = application.dispatch(self.command, self.path, self.rfile.read(length))
            self.send_response(response.status)
            self.send_header("Content-Type", response.content_type)
            self.send_header("Content-Length", str(len(response.body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(response.body)

        do_GET = _respond
        do_POST = _respond
        do_PUT = _respond

        def log_message(self, format: str, *args: object) -> None:
            print(f"{self.address_string()} - {format % args}")

    return RequestHandler


def serve(database: str | Path, host: str = "127.0.0.1", port: int = 8765) -> None:
    application = WebApplication(database)
    server = ThreadingHTTPServer((host, port), make_handler(application))
    print(f"ScheduleGenerator UI: http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=Path("schedule-generator.db"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    serve(args.database, args.host, args.port)


if __name__ == "__main__":
    main()
