"""Runtime configuration, structured logging, and in-process metrics."""

from __future__ import annotations

import json
import logging
import os
import re
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Mapping


ENVIRONMENTS = ("development", "test", "production")
LOG_FORMATS = ("json", "text")


def _boolean(value: str) -> bool:
    normalized = value.strip().casefold()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"invalid boolean value: {value}")


@dataclass(frozen=True)
class AppConfig:
    """Validated process configuration loaded from ``SG_*`` variables."""

    environment: str = "development"
    database: Path = Path("schedule-generator.db")
    host: str = "127.0.0.1"
    port: int = 8765
    secure_cookie: bool = False
    log_level: str = "INFO"
    log_format: str = "text"
    metrics_token: str | None = None

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> AppConfig:
        values = os.environ if environ is None else environ
        environment = values.get("SG_ENVIRONMENT", "development").casefold()
        config = cls(
            environment=environment,
            database=Path(values.get("SG_DATABASE", "schedule-generator.db")),
            host=values.get("SG_HOST", "127.0.0.1"),
            port=int(values.get("SG_PORT", "8765")),
            secure_cookie=_boolean(values.get("SG_SECURE_COOKIE", "false")),
            log_level=values.get("SG_LOG_LEVEL", "INFO").upper(),
            log_format=values.get("SG_LOG_FORMAT", "text").casefold(),
            metrics_token=values.get("SG_METRICS_TOKEN") or None,
        )
        config.validate()
        return config

    def validate(self) -> None:
        if self.environment not in ENVIRONMENTS:
            raise ValueError(f"SG_ENVIRONMENT must be one of {', '.join(ENVIRONMENTS)}")
        if not 1 <= self.port <= 65535:
            raise ValueError("SG_PORT must be between 1 and 65535")
        if self.log_format not in LOG_FORMATS:
            raise ValueError(f"SG_LOG_FORMAT must be one of {', '.join(LOG_FORMATS)}")
        if self.log_level not in logging.getLevelNamesMapping():
            raise ValueError("SG_LOG_LEVEL is not a recognized logging level")
        if self.environment == "production" and not self.secure_cookie:
            raise ValueError("SG_SECURE_COOKIE must be true in production")
        if self.environment == "production" and not self.metrics_token:
            raise ValueError("SG_METRICS_TOKEN must be set in production")


class JsonFormatter(logging.Formatter):
    """Emit one machine-readable JSON object per log record."""

    RESERVED = set(logging.makeLogRecord({}).__dict__)

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in self.RESERVED and key not in {"message", "asctime"}:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str, separators=(",", ":"))


def configure_logging(level: str = "INFO", log_format: str = "text") -> None:
    handler = logging.StreamHandler()
    if log_format == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


def normalized_route(path: str) -> str:
    """Collapse identifiers so metrics do not create unbounded label values."""

    route = path.split("?", 1)[0]
    route = re.sub(r"^/api/(jobs|drafts|publications|users)/[^/]+", r"/api/\1/{id}", route)
    if route.startswith("/downloads/"):
        return "/downloads/{artifact}"
    return route


class OperationalMetrics:
    """Small thread-safe Prometheus metric registry for one application process."""

    def __init__(self) -> None:
        self.started = perf_counter()
        self._lock = threading.Lock()
        self._http: dict[tuple[str, str, int], tuple[int, float]] = {}
        self._jobs: dict[str, tuple[int, float]] = {}

    def observe_http(self, method: str, path: str, status: int, duration: float) -> None:
        key = (method, normalized_route(path), status)
        with self._lock:
            count, total = self._http.get(key, (0, 0.0))
            self._http[key] = count + 1, total + duration

    def observe_job(self, status: str, duration: float) -> None:
        with self._lock:
            count, total = self._jobs.get(status, (0, 0.0))
            self._jobs[status] = count + 1, total + duration

    def render(self) -> str:
        lines = [
            "# HELP schedule_generator_up Whether the process is serving requests.",
            "# TYPE schedule_generator_up gauge",
            "schedule_generator_up 1",
            "# HELP schedule_generator_process_uptime_seconds Process uptime.",
            "# TYPE schedule_generator_process_uptime_seconds gauge",
            f"schedule_generator_process_uptime_seconds {perf_counter() - self.started:.6f}",
            "# HELP schedule_generator_http_requests_total HTTP requests.",
            "# TYPE schedule_generator_http_requests_total counter",
        ]
        with self._lock:
            http = dict(self._http)
            jobs = dict(self._jobs)
        for (method, route, status), (count, duration) in sorted(http.items()):
            labels = f'method="{method}",route="{route}",status="{status}"'
            lines.append(f"schedule_generator_http_requests_total{{{labels}}} {count}")
            lines.append(
                f"schedule_generator_http_request_duration_seconds_sum{{{labels}}} {duration:.6f}"
            )
        lines.extend(
            [
                "# HELP schedule_generator_generation_jobs_total Completed generation jobs.",
                "# TYPE schedule_generator_generation_jobs_total counter",
            ]
        )
        for status, (count, duration) in sorted(jobs.items()):
            lines.append(
                f'schedule_generator_generation_jobs_total{{status="{status}"}} {count}'
            )
            lines.append(
                "schedule_generator_generation_duration_seconds_sum"
                f'{{status="{status}"}} {duration:.6f}'
            )
        return "\n".join(lines) + "\n"
