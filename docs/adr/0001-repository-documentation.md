# ADR 0001: Maintain project documentation in the repository

- **Status:** Accepted
- **Date:** 2026-07-13
- **Owner:** [@kolyachkodenis](https://github.com/kolyachkodenis)

## Context

Product terminology, scope, and technical decisions must evolve with the implementation. Documentation stored separately from the source code is likely to become outdated and is harder to review alongside changes.

## Decision

Maintain the project charter, roadmap, glossary, contribution guide, and architecture decision records as version-controlled Markdown files in this repository. Changes follow the same review and automated-check process as code.

## Alternatives considered

- **External wiki:** easier for non-technical editing, but changes are not naturally reviewed with code and may drift from a release.
- **Issue-only documentation:** useful for discussion, but unsuitable as a stable source of truth.
- **Code comments:** appropriate for local implementation details, not product scope or cross-cutting decisions.

## Consequences

- Documentation changes are traceable and reviewable.
- Contributors can work offline and see documentation for any historical revision.
- Repository checks must validate documentation quality and links.
- School-side stakeholders may eventually need a friendlier published view or contribution workflow.

