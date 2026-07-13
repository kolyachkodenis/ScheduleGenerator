"""Public API for the ScheduleGenerator scheduling core."""

from schedule_generator.api import (
    Diagnostic,
    GenerationOptions,
    GenerationResult,
    GenerationStatus,
    LessonAssignment,
    QualityReport,
    SchedulingProblem,
    generate_schedule,
)

__all__ = [
    "Diagnostic",
    "GenerationOptions",
    "GenerationResult",
    "GenerationStatus",
    "LessonAssignment",
    "QualityReport",
    "SchedulingProblem",
    "generate_schedule",
]

__version__ = "0.2.0"
