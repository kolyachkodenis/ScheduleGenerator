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

## Publication

`PublicationService` approves a conflict-free immutable draft version, generates class and teacher views in XLSX and PDF, and controls whether those files are available for download. Artifact metadata includes a SHA-256 digest so distributed files can be verified. See the [publication workflow](../publication/README.md) for lifecycle and route details.

## Authentication and authorization

All workspace routes require a valid server-side session. `SecurityService` owns local accounts, role permissions, password hashing, session lifecycle, lockout, and audit records. The public surface is limited to security status, one-time bootstrap, login, and static assets. Published downloads still require reader access.

Administrators can list and update users, inspect recent audit events, and create an online SQLite backup. Passwords and session tokens are accepted only by their dedicated endpoints and never appear in returned user or audit objects. See the [security baseline](../security/README.md) for the role matrix and recovery procedure.

## Operational endpoints

- `GET /health/live` reports process liveness.
- `GET /health/ready` verifies database and data-directory readiness.
- `GET /metrics` returns Prometheus metrics and accepts the deployment metrics bearer token.

The health endpoints do not expose school data or account state. Production configuration requires
the metrics token; it is independent of user sessions and must be held by the monitoring system.

## Reference data

The service exposes read/save operations for complete school datasets and validated replacement of top-level reference collections. Invalid changes are rejected before a storage transaction begins.
