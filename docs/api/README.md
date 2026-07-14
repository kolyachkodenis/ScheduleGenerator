# Application API and generation workflow

`SchedulingService` is the stable application boundary for reference data, generation jobs, alternatives, cancellation, and manual timetable validation. It is transport-neutral so a later HTTP layer can expose the same behavior without duplicating business rules.

## Job lifecycle

Jobs move through the following states:

`PENDING -> RUNNING -> SUCCEEDED | FAILED | CANCELLED`

Creating a job pins the exact dataset revision and fingerprint. A later edit to school data therefore cannot silently change a queued run. Parameters, progress, alternatives, the selected result, and diagnostics are stored in SQLite.

```python
from schedule_generator import DatasetStore, GenerationRequest, SchedulingService

with DatasetStore("school.db") as store:
    service = SchedulingService(store)
    job = service.create_job(
        GenerationRequest(
            dataset_id="small_school_demo",
            alternatives=3,
            time_limit_seconds=10,
            seed=1,
            workers=1,
        )
    )
    completed = service.run_job(job.job_id)
```

Each alternative uses a deterministic seed (`seed`, `seed + 1`, and so on). The successful alternative with the lowest quality penalty becomes the selected result. Unsuccessful alternatives remain available for diagnostics.

## Progress and cancellation

`get_job` reports completed and total alternatives. `cancel_job` cancels a pending job immediately or marks a running job for cancellation. A running request is observed after the current solver call returns, so the configured per-alternative time limit is also the maximum cancellation delay.

## Manual validation

Pass edited assignment dictionaries to `validate_assignments`. The independent hard-constraint validator returns an empty list for a valid timetable or actionable error strings. Validation can target either the current dataset or an explicit historical revision.

## Reference data

The service exposes read/save operations for complete school datasets and validated replacement of top-level reference collections. Invalid changes are rejected before a storage transaction begins.
