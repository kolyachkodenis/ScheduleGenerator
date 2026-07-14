# ADR 0005: Use persistent transport-neutral generation jobs

- Status: Accepted
- Date: 2026-07-14

## Context

Timetable generation can take longer than an interactive request, must retain its exact inputs, and needs progress, cancellation, alternatives, results, and diagnostics. The user interface and HTTP transport have not yet been selected.

## Decision

Implement a transport-neutral `SchedulingService` backed by persistent SQLite jobs. Pin every job to a dataset revision and fingerprint. Run alternatives with deterministic consecutive seeds, persist each alternative immediately, and select the successful result with the lowest quality penalty.

Cancellation is cooperative between solver calls. Each call has an explicit time limit, which bounds cancellation latency without coupling the scheduling core to a worker framework.

## Consequences

- A future HTTP API, command-line worker, or desktop interface can reuse one workflow.
- Job history survives process restarts and provides reproducibility evidence.
- Multiple alternatives and failure diagnostics remain inspectable.
- Immediate cancellation inside a CP-SAT call requires future solver callbacks or process isolation.
