# Architecture Decision Records

Architecture decision records (ADRs) document technical choices that would otherwise be difficult to reconstruct later.

## Process

1. Copy `0000-template.md` to the next sequential number.
2. Use a short lowercase name, for example `0002-select-database.md`.
3. Set the status to `Proposed` while the decision is under review.
4. Record the context, decision, alternatives, and consequences.
5. Change the status to `Accepted` when the decision is approved.
6. Never rewrite an accepted decision to hide history; supersede it with a new ADR.

## Records

- [ADR 0001: Maintain project documentation in the repository](0001-repository-documentation.md)
- [ADR 0002: Use versioned JSON datasets for domain prototypes](0002-versioned-json-datasets.md)
- [ADR 0003: Use OR-Tools CP-SAT for the scheduling prototype](0003-use-cp-sat-for-prototype.md)
- [ADR 0004: Use SQLite for school configuration data](0004-use-sqlite-for-school-data.md)
- [ADR 0005: Use persistent transport-neutral generation jobs](0005-use-persistent-generation-jobs.md)
- [ADR 0006: Use a build-free local web interface](0006-use-local-web-interface.md)
- [ADR 0007: Use linear version history for timetable drafts](0007-use-linear-timetable-draft-history.md)
