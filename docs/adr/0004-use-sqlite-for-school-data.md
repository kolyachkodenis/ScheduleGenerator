# ADR 0004: Use SQLite for school configuration data

- Status: Accepted
- Date: 2026-07-14

## Context

The first deployable version needs durable local storage, transactional imports, revision history, exports, and backups without requiring a separately operated database server.

## Decision

Use SQLite for school configuration data. Store each canonical, schema-versioned dataset as one validated JSON document and retain every saved revision. Manage schema changes through ordered, idempotent migrations.

Imports are previewed and fully validated before a single transaction replaces the current dataset. Reference-data collections can be replaced through the storage API, but the complete dataset is validated before it is committed.

## Consequences

- Local development and single-school deployments need no database service.
- Atomic commits and SQLite's backup API protect imports and backups.
- Canonical JSON keeps storage aligned with the solver input schema.
- Reporting across individual entities is less convenient than with normalized tables; normalization can be introduced through a later migration if API usage justifies it.
