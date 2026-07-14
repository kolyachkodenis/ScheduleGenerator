# ADR 0006: Use a build-free local web interface for the first UI

- Status: Accepted
- Date: 2026-07-14

## Context

The operator needs an end-to-end interface before the deployment, identity, and production web stack are selected. The application already has a transport-neutral service and SQLite persistence.

## Decision

Build the first interface as responsive HTML, CSS, and browser JavaScript served by Python's standard-library HTTP server. Expose narrow JSON routes backed by `SchedulingService`. Keep route dispatch separately testable and run generation in background threads with independent database connections.

Bind to the loopback interface by default and avoid a frontend build step.

## Consequences

- Local users can evaluate the complete workflow with minimal setup.
- The interface has no framework or package-manager dependency.
- The stable application service remains reusable if a production HTTP framework is selected later.
- Authentication, production serving, and multi-process job execution remain future work.
