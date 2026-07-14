# ADR 0009: Use process-local operational telemetry

- **Status:** Accepted
- **Date:** 2026-07-15

## Context

The first deployable application is a single Python process with a local SQLite database. Operators
need actionable health, traffic, failure, and generation signals without adding an external runtime
dependency to the application core.

## Decision

The HTTP process emits newline-delimited structured logs, exposes liveness and readiness endpoints,
and maintains a bounded in-memory Prometheus metric registry. Production metrics require a separate
bearer token. Route labels replace record identifiers with stable placeholders. A deployment platform
is responsible for collecting stdout, scraping metrics, retaining events, and raising alerts.

## Consequences

- Local and container deployments have the same observable contract.
- The process remains usable without a monitoring service.
- Counters reset when the process restarts and are not aggregated across replicas.
- A later multi-replica deployment should replace the local registry with a shared telemetry pipeline.
