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
from schedule_generator.data_import import ImportIssue, ImportPreview, apply_import, preview_import
from schedule_generator.jobs import (
    GenerationAlternative,
    GenerationJob,
    GenerationRequest,
    JobStatus,
    SchedulingService,
)
from schedule_generator.storage import DatasetStore, StoredDataset

__all__ = [
    "Diagnostic",
    "GenerationOptions",
    "GenerationResult",
    "GenerationStatus",
    "LessonAssignment",
    "QualityReport",
    "SchedulingProblem",
    "generate_schedule",
    "DatasetStore",
    "StoredDataset",
    "ImportIssue",
    "ImportPreview",
    "preview_import",
    "apply_import",
    "GenerationAlternative",
    "GenerationJob",
    "GenerationRequest",
    "JobStatus",
    "SchedulingService",
]

__version__ = "0.5.0"
