"""Public, solver-neutral API for timetable generation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping


class GenerationStatus(str, Enum):
    """Stable outcome states exposed by the scheduling core."""

    OPTIMAL = "OPTIMAL"
    FEASIBLE = "FEASIBLE"
    INFEASIBLE = "INFEASIBLE"
    UNKNOWN = "UNKNOWN"
    INVALID_INPUT = "INVALID_INPUT"
    INPUT_INFEASIBLE = "INPUT_INFEASIBLE"
    INVALID_SOLUTION = "INVALID_SOLUTION"


@dataclass(frozen=True)
class GenerationOptions:
    """Explicit controls that make a generation run reproducible."""

    time_limit_seconds: float = 10.0
    seed: int = 1
    workers: int = 1

    def __post_init__(self) -> None:
        if self.time_limit_seconds <= 0:
            raise ValueError("time_limit_seconds must be greater than zero")
        if self.seed < 0:
            raise ValueError("seed must be non-negative")
        if self.workers < 1:
            raise ValueError("workers must be at least one")


@dataclass(frozen=True)
class SchedulingProblem:
    """Immutable, canonical dataset passed to any solver backend."""

    dataset_id: str
    schema_version: str
    fingerprint: str
    _canonical_json: str

    @classmethod
    def from_mapping(cls, dataset: Mapping[str, Any]) -> SchedulingProblem:
        if not isinstance(dataset, Mapping):
            raise TypeError("dataset must be a mapping")
        canonical = json.dumps(
            dict(dataset),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        decoded = json.loads(canonical)
        dataset_id = decoded.get("dataset_id")
        schema_version = decoded.get("schema_version")
        if not isinstance(dataset_id, str) or not dataset_id:
            raise ValueError("dataset_id must be a non-empty string")
        if not isinstance(schema_version, str) or not schema_version:
            raise ValueError("schema_version must be a non-empty string")
        fingerprint = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return cls(dataset_id, schema_version, fingerprint, canonical)

    def to_mapping(self) -> dict[str, Any]:
        """Return a fresh mapping so a backend cannot mutate the problem."""

        return json.loads(self._canonical_json)

    @property
    def metadata(self) -> Mapping[str, str]:
        return MappingProxyType(
            {
                "dataset_id": self.dataset_id,
                "schema_version": self.schema_version,
                "fingerprint": self.fingerprint,
            }
        )


@dataclass(frozen=True)
class Diagnostic:
    code: str
    message: str
    details: Mapping[str, Any]


@dataclass(frozen=True)
class LessonAssignment:
    id: str
    requirement_id: str
    occurrence_index: int
    day_id: str
    start_period_id: str
    occupied_period_ids: tuple[str, ...]
    teacher_id: str
    classroom_id: str


@dataclass(frozen=True)
class ConstraintQuality:
    constraint_id: str
    raw_penalty: int
    weighted_penalty: int


@dataclass(frozen=True)
class QualityViolation:
    constraint_id: str
    description: str
    value: int
    weight: int
    weighted_penalty: int


@dataclass(frozen=True)
class QualityReport:
    total_penalty: int
    by_constraint: tuple[ConstraintQuality, ...]
    violations: tuple[QualityViolation, ...]


@dataclass(frozen=True)
class SolverStatistics:
    name: str
    version: str
    python: str
    seed: int
    workers: int
    time_limit_seconds: float
    wall_time_seconds: float
    objective: float | None
    best_bound: float | None
    branches: int
    conflicts: int
    variables: int
    constraints: int


@dataclass(frozen=True)
class GenerationResult:
    dataset_id: str
    dataset_fingerprint: str
    status: GenerationStatus
    assignments: tuple[LessonAssignment, ...]
    quality: QualityReport | None
    diagnostics: tuple[Diagnostic, ...]
    validation_errors: tuple[str, ...]
    solver: SolverStatistics | None

    @property
    def is_success(self) -> bool:
        return self.status in {GenerationStatus.OPTIMAL, GenerationStatus.FEASIBLE}

    @classmethod
    def from_backend(
        cls, problem: SchedulingProblem, raw: Mapping[str, Any]
    ) -> GenerationResult:
        status = GenerationStatus(raw["status"])
        assignments = tuple(
            LessonAssignment(
                id=item["id"],
                requirement_id=item["requirement_id"],
                occurrence_index=item["occurrence_index"],
                day_id=item["slot"]["day_id"],
                start_period_id=item["slot"]["period_id"],
                occupied_period_ids=tuple(item["occupied_period_ids"]),
                teacher_id=item["teacher_id"],
                classroom_id=item["classroom_id"],
            )
            for item in raw.get("assignments", [])
        )

        raw_quality = raw.get("quality_report")
        quality = None
        if raw_quality is not None:
            quality = QualityReport(
                total_penalty=int(raw_quality["total_penalty"]),
                by_constraint=tuple(
                    ConstraintQuality(
                        constraint_id=constraint_id,
                        raw_penalty=int(values["raw"]),
                        weighted_penalty=int(values["weighted"]),
                    )
                    for constraint_id, values in sorted(
                        raw_quality["by_constraint"].items()
                    )
                ),
                violations=tuple(
                    QualityViolation(
                        constraint_id=item["constraint_id"],
                        description=item["description"],
                        value=int(item["value"]),
                        weight=int(item["weight"]),
                        weighted_penalty=int(item["weighted_penalty"]),
                    )
                    for item in raw_quality["violations"]
                ),
            )

        diagnostics = []
        for item in raw.get("diagnostics", []):
            if isinstance(item, str):
                diagnostics.append(
                    Diagnostic("INPUT_VALIDATION_ERROR", item, MappingProxyType({}))
                )
                continue
            details = {
                key: value for key, value in item.items() if key not in {"code", "message"}
            }
            diagnostics.append(
                Diagnostic(
                    code=item.get("code", "UNSPECIFIED"),
                    message=item.get("message", "No diagnostic message provided."),
                    details=MappingProxyType(details),
                )
            )

        raw_solver = raw.get("solver")
        solver = SolverStatistics(**raw_solver) if raw_solver else None
        return cls(
            dataset_id=problem.dataset_id,
            dataset_fingerprint=problem.fingerprint,
            status=status,
            assignments=assignments,
            quality=quality,
            diagnostics=tuple(diagnostics),
            validation_errors=tuple(raw.get("validation_errors", [])),
            solver=solver,
        )

    def to_dict(self) -> dict[str, Any]:
        quality = None
        if self.quality:
            quality = {
                "total_penalty": self.quality.total_penalty,
                "by_constraint": {
                    item.constraint_id: {
                        "raw": item.raw_penalty,
                        "weighted": item.weighted_penalty,
                    }
                    for item in self.quality.by_constraint
                },
                "violations": [asdict(item) for item in self.quality.violations],
            }
        return {
            "dataset_id": self.dataset_id,
            "dataset_fingerprint": self.dataset_fingerprint,
            "status": self.status.value,
            "solver": asdict(self.solver) if self.solver else None,
            "assignments": [
                {
                    "id": item.id,
                    "requirement_id": item.requirement_id,
                    "occurrence_index": item.occurrence_index,
                    "slot": {
                        "day_id": item.day_id,
                        "period_id": item.start_period_id,
                    },
                    "occupied_period_ids": list(item.occupied_period_ids),
                    "teacher_id": item.teacher_id,
                    "classroom_id": item.classroom_id,
                }
                for item in self.assignments
            ],
            "quality_report": quality,
            "diagnostics": [
                {
                    "code": item.code,
                    "message": item.message,
                    **dict(item.details),
                }
                for item in self.diagnostics
            ],
            "validation_errors": list(self.validation_errors),
        }


def generate_schedule(
    problem: SchedulingProblem | Mapping[str, Any],
    options: GenerationOptions | None = None,
) -> GenerationResult:
    """Validate, generate, verify, and return a typed timetable result."""

    if not isinstance(problem, SchedulingProblem):
        problem = SchedulingProblem.from_mapping(problem)
    options = options or GenerationOptions()

    # The backend is imported lazily so domain objects and result types do not
    # require OR-Tools until a generation run actually starts.
    from schedule_generator.prototype import solve_dataset

    raw = solve_dataset(
        problem.to_mapping(),
        time_limit=options.time_limit_seconds,
        seed=options.seed,
        workers=options.workers,
    )
    return GenerationResult.from_backend(problem, raw)
