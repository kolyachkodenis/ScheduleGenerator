"""Small local HTTP application for the first operator interface."""

from __future__ import annotations

import argparse
import hmac
import json
import logging
import mimetypes
import os
import threading
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, Mapping
from urllib.parse import unquote, urlparse

from schedule_generator.api import GenerationOptions
from schedule_generator.editing import TimetableDraft, TimetableEditingService
from schedule_generator.jobs import GenerationJob, GenerationRequest, SchedulingService
from schedule_generator.operations import (
    AppConfig,
    OperationalMetrics,
    configure_logging,
    normalized_route,
)
from schedule_generator.publication import PublicationService
from schedule_generator.security import (
    ROLE_PERMISSIONS,
    AuthenticationError,
    AuthorizationError,
    SecurityService,
    User,
)
from schedule_generator.storage import DatasetStore


ASSET_ROOT = Path(__file__).with_name("web")
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEMO_PATH = PROJECT_ROOT / "examples" / "small-school.json"
LOGGER = logging.getLogger("schedule_generator.web")


@dataclass(frozen=True)
class WebResponse:
    status: int
    body: bytes
    content_type: str = "application/json; charset=utf-8"
    headers: tuple[tuple[str, str], ...] = ()

    @classmethod
    def json(
        cls,
        status: int,
        value: Any,
        headers: tuple[tuple[str, str], ...] = (),
    ) -> WebResponse:
        return cls(
            status,
            (json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n").encode(
                "utf-8"
            ),
            headers=headers,
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
        secure_cookie: bool = False,
        environment: str = "development",
        metrics_token: str | None = None,
        metrics: OperationalMetrics | None = None,
        service_factory: Callable[[DatasetStore], SchedulingService] = SchedulingService,
        editing_factory: Callable[[DatasetStore], TimetableEditingService] = TimetableEditingService,
    ) -> None:
        self.database = Path(database)
        self.run_in_background = run_in_background
        self.secure_cookie = secure_cookie
        self.environment = environment
        self.metrics_token = metrics_token
        self.metrics = metrics or OperationalMetrics()
        self.service_factory = service_factory
        self.editing_factory = editing_factory

    def _service(self) -> tuple[DatasetStore, SchedulingService]:
        store = DatasetStore(self.database)
        return store, self.service_factory(store)

    def _editing(self) -> tuple[DatasetStore, TimetableEditingService]:
        store = DatasetStore(self.database)
        return store, self.editing_factory(store)

    def _publication(self) -> tuple[DatasetStore, PublicationService]:
        store = DatasetStore(self.database)
        return store, PublicationService(store, self.database.parent / "published")

    def dispatch(
        self,
        method: str,
        raw_path: str,
        body: bytes = b"",
        headers: Mapping[str, str] | None = None,
    ) -> WebResponse:
        path = unquote(urlparse(raw_path).path)
        request_headers = {key.casefold(): value for key, value in (headers or {}).items()}
        try:
            if method == "GET" and path == "/health/live":
                return self._health_live()
            if method == "GET" and path == "/health/ready":
                return self._health_ready()
            if method == "GET" and path == "/metrics":
                return self._metrics(request_headers)
            if method == "GET" and path in {"/", "/index.html"}:
                return self._asset("index.html")
            if method == "GET" and path.startswith("/assets/"):
                return self._asset(path.removeprefix("/assets/"))
            payload = json.loads(body.decode("utf-8")) if body else {}
            if not isinstance(payload, dict):
                raise ValueError("request body must be a JSON object")
            if method == "GET" and path == "/api/security/status":
                return self._security_status(request_headers)
            if method == "POST" and path == "/api/security/bootstrap":
                return self._bootstrap(payload)
            if method == "POST" and path == "/api/security/login":
                return self._login(payload)
            if method == "POST" and path == "/api/security/logout":
                user, token = self._authorize(request_headers, "workspace:read")
                return self._logout(user, token)
            if method == "GET" and path.startswith("/downloads/"):
                user, _token = self._authorize(request_headers, "workspace:read")
                return self._download(path.removeprefix("/downloads/"), user)
            if method == "GET" and path == "/api/state":
                user, _token = self._authorize(request_headers, "workspace:read")
                return self._state(user)
            if method == "GET" and path == "/api/users":
                user, _token = self._authorize(request_headers, "security:admin")
                return self._list_users(user)
            if method == "POST" and path == "/api/users":
                user, _token = self._authorize(request_headers, "security:admin")
                return self._create_user(payload, user)
            if method == "PUT" and path.startswith("/api/users/"):
                user, _token = self._authorize(request_headers, "security:admin")
                return self._update_user(path.removeprefix("/api/users/"), payload, user)
            if method == "GET" and path == "/api/audit":
                user, _token = self._authorize(request_headers, "security:admin")
                return self._audit_events(user)
            if method == "POST" and path == "/api/admin/backup":
                user, _token = self._authorize(request_headers, "security:admin")
                return self._backup(user)
            if method == "POST" and path == "/api/demo":
                user, _token = self._authorize(request_headers, "data:write")
                return self._load_demo(user)
            if method == "POST" and path == "/api/jobs":
                user, _token = self._authorize(request_headers, "generation:write")
                return self._create_job(payload, user)
            if path.startswith("/api/jobs/"):
                job_id, action = self._job_path(path)
                if method == "GET" and action is None:
                    self._authorize(request_headers, "workspace:read")
                    return self._get_job(job_id)
                if method == "POST" and action == "cancel":
                    user, _token = self._authorize(request_headers, "generation:write")
                    return self._cancel_job(job_id, user)
                if method == "POST" and action == "draft":
                    user, _token = self._authorize(request_headers, "draft:write")
                    return self._create_draft(job_id, user)
            if path.startswith("/api/drafts/"):
                draft_id, action = self._draft_path(path)
                if method == "GET" and action is None:
                    self._authorize(request_headers, "workspace:read")
                    return self._get_draft(draft_id)
                if method == "POST":
                    permission = "publication:write" if action == "approve" else "draft:write"
                    user, _token = self._authorize(request_headers, permission)
                    return self._edit_draft(draft_id, action, payload, user)
            if method == "POST" and path.startswith("/api/publications/"):
                publication_id, action = self._publication_path(path)
                user, _token = self._authorize(request_headers, "publication:write")
                return self._change_publication(publication_id, action, user)
            if method == "PUT" and path.startswith("/api/datasets/"):
                user, _token = self._authorize(request_headers, "data:write")
                return self._replace_collection(path, payload, user)
            if method == "POST" and path == "/api/validate":
                self._authorize(request_headers, "draft:write")
                return self._validate(payload)
            return WebResponse.json(HTTPStatus.NOT_FOUND, {"error": "route not found"})
        except AuthenticationError as error:
            return WebResponse.json(HTTPStatus.UNAUTHORIZED, {"error": str(error)})
        except AuthorizationError as error:
            return WebResponse.json(HTTPStatus.FORBIDDEN, {"error": str(error)})
        except (KeyError, ValueError, json.JSONDecodeError, UnicodeError) as error:
            return WebResponse.json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
        except Exception as error:
            LOGGER.exception(
                "request failed",
                extra={"event": "request.failed", "method": method, "path": path},
            )
            payload = {"error": "request failed"}
            if self.environment == "development":
                payload["detail"] = str(error)
            return WebResponse.json(HTTPStatus.INTERNAL_SERVER_ERROR, payload)

    def _health_live(self) -> WebResponse:
        return WebResponse.json(
            HTTPStatus.OK,
            {"status": "ok", "environment": self.environment},
        )

    def _health_ready(self) -> WebResponse:
        checks: dict[str, str] = {}
        try:
            self.database.parent.mkdir(parents=True, exist_ok=True)
            store = DatasetStore(self.database)
            try:
                store.connection.execute("SELECT 1").fetchone()
                checks["database"] = "ok"
            finally:
                store.close()
            checks["data_directory"] = (
                "ok" if os.access(self.database.parent, os.W_OK) else "not_writable"
            )
        except Exception:
            LOGGER.exception("readiness check failed", extra={"event": "health.not_ready"})
            checks.setdefault("database", "error")
        ready = all(value == "ok" for value in checks.values())
        return WebResponse.json(
            HTTPStatus.OK if ready else HTTPStatus.SERVICE_UNAVAILABLE,
            {"status": "ready" if ready else "not_ready", "checks": checks},
        )

    def _metrics(self, headers: Mapping[str, str]) -> WebResponse:
        if self.metrics_token:
            supplied = headers.get("authorization", "").removeprefix("Bearer ").strip()
            if not hmac.compare_digest(supplied, self.metrics_token):
                return WebResponse.json(HTTPStatus.UNAUTHORIZED, {"error": "invalid metrics token"})
        return WebResponse(
            HTTPStatus.OK,
            self.metrics.render().encode("utf-8"),
            "text/plain; version=0.0.4; charset=utf-8",
        )

    @staticmethod
    def _session_token(headers: Mapping[str, str]) -> str | None:
        authorization = headers.get("authorization", "")
        if authorization.startswith("Bearer "):
            return authorization.removeprefix("Bearer ").strip()
        cookie = SimpleCookie()
        cookie.load(headers.get("cookie", ""))
        return cookie["sg_session"].value if "sg_session" in cookie else None

    def _authorize(
        self, headers: Mapping[str, str], permission: str
    ) -> tuple[User, str]:
        token = self._session_token(headers)
        store = DatasetStore(self.database)
        try:
            security = SecurityService(store)
            user = security.authenticate(token)
            security.require(user, permission)
            return user, token or ""
        finally:
            store.close()

    def _session_cookie(self, token: str, max_age: int = 43_200) -> tuple[str, str]:
        value = (
            f"sg_session={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age={max_age}"
            if token
            else "sg_session=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0"
        )
        if self.secure_cookie:
            value += "; Secure"
        return "Set-Cookie", value

    def _security_status(self, headers: Mapping[str, str]) -> WebResponse:
        store = DatasetStore(self.database)
        try:
            security = SecurityService(store)
            user = None
            try:
                user = security.authenticate(self._session_token(headers))
            except AuthenticationError:
                pass
            return WebResponse.json(
                HTTPStatus.OK,
                {
                    "initialized": security.has_users(),
                    "authenticated": user is not None,
                    "user": user.to_dict() if user else None,
                },
            )
        finally:
            store.close()

    def _bootstrap(self, payload: dict[str, Any]) -> WebResponse:
        store = DatasetStore(self.database)
        try:
            security = SecurityService(store)
            user = security.bootstrap(
                str(payload.get("username", "")), str(payload.get("password", ""))
            )
            session = security.login(user.username, str(payload.get("password", "")))
            return WebResponse.json(
                HTTPStatus.CREATED,
                {"user": session.user.to_dict(), "expires_at": session.expires_at},
                (self._session_cookie(session.token),),
            )
        finally:
            store.close()

    def _login(self, payload: dict[str, Any]) -> WebResponse:
        store = DatasetStore(self.database)
        try:
            session = SecurityService(store).login(
                str(payload.get("username", "")), str(payload.get("password", ""))
            )
            return WebResponse.json(
                HTTPStatus.OK,
                {"user": session.user.to_dict(), "expires_at": session.expires_at},
                (self._session_cookie(session.token),),
            )
        finally:
            store.close()

    def _logout(self, user: User, token: str) -> WebResponse:
        store = DatasetStore(self.database)
        try:
            SecurityService(store).logout(token, user)
            return WebResponse.json(
                HTTPStatus.OK, {"logged_out": True}, (self._session_cookie("", 0),)
            )
        finally:
            store.close()

    def _audit(
        self,
        user: User,
        action: str,
        target_type: str,
        target_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        store = DatasetStore(self.database)
        try:
            SecurityService(store).audit(
                user.user_id, action, target_type, target_id, details=details
            )
        finally:
            store.close()

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

    def _state(self, user: User) -> WebResponse:
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
            publications = [
                publication.to_dict()
                for publication in PublicationService(
                    store, self.database.parent / "published"
                ).list()
            ]
            return WebResponse.json(
                HTTPStatus.OK,
                {
                    "datasets": datasets,
                    "jobs": jobs,
                    "drafts": drafts,
                    "publications": publications,
                    "current_user": user.to_dict(),
                    "permissions": sorted(ROLE_PERMISSIONS[user.role]),
                },
            )
        finally:
            store.close()

    def _load_demo(self, user: User) -> WebResponse:
        dataset = json.loads(DEMO_PATH.read_text(encoding="utf-8"))
        store, service = self._service()
        try:
            saved = service.save_reference_data(dataset)
            response = WebResponse.json(
                HTTPStatus.CREATED,
                {"dataset_id": saved.dataset_id, "revision": saved.revision},
            )
            self._audit(user, "dataset.demo_loaded", "dataset", saved.dataset_id)
            return response
        finally:
            store.close()

    def _replace_collection(
        self, path: str, payload: dict[str, Any], user: User
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
            response = WebResponse.json(
                HTTPStatus.OK,
                {"dataset_id": saved.dataset_id, "revision": saved.revision},
            )
            self._audit(
                user,
                "dataset.collection_replaced",
                "dataset",
                saved.dataset_id,
                {"collection": collection, "revision": saved.revision},
            )
            return response
        finally:
            store.close()

    def _create_job(self, payload: dict[str, Any], user: User) -> WebResponse:
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
            response = self._get_job(job.job_id, status=HTTPStatus.CREATED)
            self._audit(user, "generation.created", "job", job.job_id)
            return response
        self._audit(user, "generation.created", "job", job.job_id)
        return WebResponse.json(HTTPStatus.ACCEPTED, job_to_dict(job))

    def _run_job(self, job_id: str) -> None:
        started = perf_counter()
        store, service = self._service()
        try:
            job = service.run_job(job_id)
            self.metrics.observe_job(job.status.value, perf_counter() - started)
            LOGGER.info(
                "generation job finished",
                extra={
                    "event": "generation.finished",
                    "job_id": job_id,
                    "status": job.status.value,
                    "duration_seconds": round(perf_counter() - started, 6),
                },
            )
        except Exception:
            self.metrics.observe_job("ERROR", perf_counter() - started)
            LOGGER.exception(
                "generation job crashed",
                extra={"event": "generation.crashed", "job_id": job_id},
            )
            raise
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

    def _cancel_job(self, job_id: str, user: User) -> WebResponse:
        store, service = self._service()
        try:
            response = WebResponse.json(
                HTTPStatus.OK, job_to_dict(service.cancel_job(job_id))
            )
            self._audit(user, "generation.cancelled", "job", job_id)
            return response
        finally:
            store.close()

    @staticmethod
    def _draft_path(path: str) -> tuple[str, str | None]:
        parts = path.strip("/").split("/")
        if len(parts) not in {3, 4}:
            raise ValueError("invalid draft route")
        return parts[2], parts[3] if len(parts) == 4 else None

    def _create_draft(self, job_id: str, user: User) -> WebResponse:
        store, editing = self._editing()
        try:
            draft = editing.create_from_job(job_id)
            response = WebResponse.json(HTTPStatus.CREATED, draft_to_dict(draft))
            self._audit(user, "draft.created", "draft", draft.draft_id, {"job_id": job_id})
            return response
        finally:
            store.close()

    def _get_draft(self, draft_id: str) -> WebResponse:
        store, editing = self._editing()
        try:
            return WebResponse.json(HTTPStatus.OK, draft_to_dict(editing.get(draft_id)))
        finally:
            store.close()

    def _edit_draft(
        self,
        draft_id: str,
        action: str | None,
        payload: dict[str, Any],
        user: User,
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
                response = WebResponse.json(HTTPStatus.OK, draft_to_dict(draft))
                self._audit(user, "draft.moved", "draft", draft_id, {"assignment_id": payload.get("assignment_id")})
                return response
            if action == "lock":
                draft = editing.set_lock(
                    draft_id,
                    str(payload.get("assignment_id", "")),
                    bool(payload.get("locked", True)),
                )
                response = WebResponse.json(HTTPStatus.OK, draft_to_dict(draft))
                self._audit(user, "draft.lock_changed", "draft", draft_id, {"assignment_id": payload.get("assignment_id"), "locked": bool(payload.get("locked", True))})
                return response
            if action == "undo":
                draft = editing.undo(draft_id)
                self._audit(user, "draft.undo", "draft", draft_id)
                return WebResponse.json(HTTPStatus.OK, draft_to_dict(draft))
            if action == "redo":
                draft = editing.redo(draft_id)
                self._audit(user, "draft.redo", "draft", draft_id)
                return WebResponse.json(HTTPStatus.OK, draft_to_dict(draft))
            if action == "regenerate":
                options = GenerationOptions(
                    float(payload.get("time_limit_seconds", 10)),
                    int(payload.get("seed", 1)),
                    int(payload.get("workers", 1)),
                )
                draft = editing.regenerate(draft_id, options)
                self._audit(user, "draft.regenerated", "draft", draft_id)
                return WebResponse.json(HTTPStatus.OK, draft_to_dict(draft))
            if action == "compare":
                return WebResponse.json(
                    HTTPStatus.OK,
                    editing.compare(
                        draft_id, int(payload.get("left", 0)), int(payload["right"])
                    ),
                )
            if action == "approve":
                publications = PublicationService(
                    store, self.database.parent / "published"
                )
                publication = publications.approve(draft_id)
                self._audit(
                    user,
                    "publication.approved",
                    "publication",
                    publication.publication_id,
                    {"draft_id": draft_id, "version": publication.version},
                )
                return WebResponse.json(HTTPStatus.CREATED, publication.to_dict())
            raise ValueError("unknown draft action")
        finally:
            store.close()

    @staticmethod
    def _publication_path(path: str) -> tuple[str, str]:
        parts = path.strip("/").split("/")
        if len(parts) != 4 or parts[3] not in {"publish", "unpublish"}:
            raise ValueError("invalid publication route")
        return parts[2], parts[3]

    def _change_publication(
        self, publication_id: str, action: str, user: User
    ) -> WebResponse:
        store, publications = self._publication()
        try:
            publication = (
                publications.publish(publication_id)
                if action == "publish"
                else publications.unpublish(publication_id)
            )
            self._audit(
                user,
                f"publication.{action}ed",
                "publication",
                publication_id,
                {"version": publication.version},
            )
            return WebResponse.json(HTTPStatus.OK, publication.to_dict())
        finally:
            store.close()

    def _download(self, filename: str, user: User) -> WebResponse:
        store, publications = self._publication()
        try:
            path, content_type = publications.download(filename)
            response = WebResponse(HTTPStatus.OK, path.read_bytes(), content_type)
            self._audit(user, "publication.downloaded", "artifact", filename)
            return response
        finally:
            store.close()

    def _list_users(self, _actor: User) -> WebResponse:
        store = DatasetStore(self.database)
        try:
            return WebResponse.json(
                HTTPStatus.OK,
                {"users": [item.to_dict() for item in SecurityService(store).list_users()]},
            )
        finally:
            store.close()

    def _create_user(self, payload: dict[str, Any], actor: User) -> WebResponse:
        store = DatasetStore(self.database)
        try:
            security = SecurityService(store)
            user = security.create_user(
                str(payload.get("username", "")),
                str(payload.get("password", "")),
                str(payload.get("role", "reader")),
            )
            security.audit(
                actor.user_id,
                "user.created",
                "user",
                user.user_id,
                details={"role": user.role},
            )
            return WebResponse.json(HTTPStatus.CREATED, user.to_dict())
        finally:
            store.close()

    def _update_user(
        self, user_id: str, payload: dict[str, Any], actor: User
    ) -> WebResponse:
        store = DatasetStore(self.database)
        try:
            security = SecurityService(store)
            if "password" in payload and ({"role", "enabled"} & payload.keys()):
                raise ValueError("password reset must be a separate request")
            if "password" in payload:
                security.reset_password(user_id, str(payload["password"]))
                security.audit(actor.user_id, "user.password_reset", "user", user_id)
            user = security.update_user(
                user_id,
                role=str(payload["role"]) if "role" in payload else None,
                enabled=bool(payload["enabled"]) if "enabled" in payload else None,
            )
            security.audit(
                actor.user_id,
                "user.updated",
                "user",
                user_id,
                details={"role": user.role, "enabled": user.enabled},
            )
            return WebResponse.json(HTTPStatus.OK, user.to_dict())
        finally:
            store.close()

    def _audit_events(self, _actor: User) -> WebResponse:
        store = DatasetStore(self.database)
        try:
            events = SecurityService(store).list_audit_events()
            return WebResponse.json(
                HTTPStatus.OK, {"events": [event.to_dict() for event in events]}
            )
        finally:
            store.close()

    def _backup(self, actor: User) -> WebResponse:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        destination = self.database.parent / "backups" / f"schedule-generator-{timestamp}.db"
        store = DatasetStore(self.database)
        try:
            path = store.backup(destination)
            SecurityService(store).audit(
                actor.user_id,
                "backup.created",
                "backup",
                path.name,
                details={"size": path.stat().st_size},
            )
            return WebResponse.json(
                HTTPStatus.CREATED,
                {"filename": path.name, "size": path.stat().st_size},
            )
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
            started = perf_counter()
            request_id = self.headers.get("X-Request-ID") or uuid.uuid4().hex
            length = int(self.headers.get("Content-Length", "0"))
            if length > 10_000_000:
                response = WebResponse.json(
                    HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "request too large"}
                )
            else:
                response = application.dispatch(
                    self.command,
                    self.path,
                    self.rfile.read(length),
                    {key: value for key, value in self.headers.items()},
                )
            self.send_response(response.status)
            self.send_header("Content-Type", response.content_type)
            self.send_header("Content-Length", str(len(response.body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("X-Request-ID", request_id)
            for key, value in response.headers:
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(response.body)
            duration = perf_counter() - started
            application.metrics.observe_http(
                self.command, self.path, response.status, duration
            )
            LOGGER.info(
                "request completed",
                extra={
                    "event": "http.request",
                    "request_id": request_id,
                    "method": self.command,
                    "path": normalized_route(self.path),
                    "status": response.status,
                    "duration_seconds": round(duration, 6),
                },
            )

        do_GET = _respond
        do_POST = _respond
        do_PUT = _respond

        def log_message(self, format: str, *args: object) -> None:
            return

    return RequestHandler


def serve(
    database: str | Path,
    host: str = "127.0.0.1",
    port: int = 8765,
    secure_cookie: bool = False,
    environment: str = "development",
    log_level: str = "INFO",
    log_format: str = "text",
    metrics_token: str | None = None,
) -> None:
    configure_logging(log_level, log_format)
    application = WebApplication(
        database,
        secure_cookie=secure_cookie,
        environment=environment,
        metrics_token=metrics_token,
    )
    server = ThreadingHTTPServer((host, port), make_handler(application))
    LOGGER.info(
        "server started",
        extra={
            "event": "server.started",
            "environment": environment,
            "host": host,
            "port": port,
            "database": str(database),
        },
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        LOGGER.info("server stopped", extra={"event": "server.stopped"})


def main() -> None:
    config = AppConfig.from_env()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=config.database)
    parser.add_argument("--host", default=config.host)
    parser.add_argument("--port", type=int, default=config.port)
    parser.add_argument("--environment", default=config.environment)
    parser.add_argument("--log-level", default=config.log_level)
    parser.add_argument("--log-format", choices=("text", "json"), default=config.log_format)
    parser.add_argument("--metrics-token", default=config.metrics_token)
    parser.add_argument(
        "--secure-cookie",
        action="store_true",
        default=config.secure_cookie,
        help="mark session cookies Secure when the application is served through HTTPS",
    )
    args = parser.parse_args()
    effective = AppConfig(
        environment=args.environment,
        database=args.database,
        host=args.host,
        port=args.port,
        secure_cookie=args.secure_cookie,
        log_level=args.log_level.upper(),
        log_format=args.log_format,
        metrics_token=args.metrics_token,
    )
    effective.validate()
    serve(
        effective.database,
        effective.host,
        effective.port,
        effective.secure_cookie,
        effective.environment,
        effective.log_level,
        effective.log_format,
        effective.metrics_token,
    )


if __name__ == "__main__":
    main()
