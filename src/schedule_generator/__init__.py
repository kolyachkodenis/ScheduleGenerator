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
from schedule_generator.editing import DraftVersion, TimetableDraft, TimetableEditingService
from schedule_generator.jobs import (
    GenerationAlternative,
    GenerationJob,
    GenerationRequest,
    JobStatus,
    SchedulingService,
)
from schedule_generator.publication import (
    Publication,
    PublicationService,
    export_pdf,
    export_xlsx,
    timetable_views,
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
    "DraftVersion",
    "TimetableDraft",
    "TimetableEditingService",
    "GenerationAlternative",
    "GenerationJob",
    "GenerationRequest",
    "JobStatus",
    "SchedulingService",
    "Publication",
    "PublicationService",
    "timetable_views",
    "export_xlsx",
    "export_pdf",
]

__version__ = "0.7.0"
