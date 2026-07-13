# ADR 0002: Use versioned JSON datasets for domain prototypes

- **Status:** Accepted
- **Date:** 2026-07-13
- **Owner:** [@kolyachkodenis](https://github.com/kolyachkodenis)

## Context

The solver prototype needs a deterministic, reviewable input format before a database or spreadsheet-import design is selected. The format must represent nested scheduling concepts, support automated structural validation, and remain independent of persistence technology.

## Decision

Use UTF-8 JSON documents as the exchange format for domain-model prototypes and synthetic reference datasets. Every document declares a semantic `schema_version` and is validated against a versioned JSON Schema plus repository-specific semantic checks.

JSON is an exchange and test-fixture format, not a decision about the production database or final import format. Domain code must not depend directly on JSON field layout after parsing and validation.

## Alternatives considered

- **YAML:** easier to annotate by hand, but has more parsing ambiguity and weaker default interoperability with schema tooling.
- **CSV or XLSX:** familiar to school staff, but relational references and nested policies require several coordinated tables and are better addressed during the import stage.
- **Database schema first:** useful for persistence, but prematurely couples solver exploration to storage choices.
- **Python objects only:** quick for a prototype, but fixtures become harder to review, exchange, and validate independently.

## Consequences

- Prototype inputs and expected test scenarios can be reviewed in pull requests.
- JSON Schema handles structure while a semantic validator handles references and cross-record invariants.
- Schema-version migrations will be necessary when the format changes.
- Spreadsheet import will later translate into this domain representation rather than become the domain model itself.

