# Constraint Catalog

This directory is the versioned source of truth for timetable rules. It converts discovery statements into stable identifiers that can be referenced by requirements, tests, diagnostics, configuration, and solver code.

## Status

- **Roadmap stage:** Stage 2, in progress
- **Catalog version:** Draft 0.1
- **Evidence:** Hypotheses pending school-side validation
- **Approval owner:** Unassigned school-side requirements owner

No draft rule is an approved school requirement. The catalog intentionally distinguishes likely universal validity rules from policies that may vary between schools.

## Documents

- [Rule catalog](CATALOG.md): hard constraints and soft preferences with stable IDs.
- [Priority model](PRIORITIES.md): preference tiers, weights, and scoring safeguards.
- [Examples](EXAMPLES.md): concrete valid, invalid, and trade-off scenarios.
- [Relaxation policy](RELAXATION_POLICY.md): which rules may be relaxed and how changes are audited.

## Rule lifecycle

| Status | Meaning |
| --- | --- |
| Draft | Proposed from product goals or common scheduling practice; not validated. |
| Reported | Described by a discovery participant but not yet approved. |
| Confirmed | Approved by the requirements owner with supporting evidence. |
| Rejected | Explicitly determined not to apply to the target scope. |
| Superseded | Replaced by another rule while retained for traceability. |

## Identifier policy

- Hard constraints use `HC-NNN`.
- Soft constraints use `SC-NNN`.
- Catalog examples use `CX-NNN`.
- IDs are never reused, even after a rule is rejected or superseded.
- A material semantic change creates a new ID and supersedes the old rule.
- Clarifications that do not change behavior may update the existing entry.

## Required rule fields

Every rule must eventually define:

- stable identifier and name;
- rule type and validation status;
- business statement in solver-independent language;
- applicability and scope;
- required input data;
- violation or penalty measurement;
- diagnostic information shown to a scheduler;
- source evidence and approval;
- at least one positive and one negative test example.

## Stage 2 completion gate

Stage 2 may move to `Complete` when:

- all MVP rules discovered in Stage 1 have catalog IDs;
- every hard rule has explicit applicability and violation semantics;
- every soft rule has an approved priority tier and penalty direction;
- school-specific policies are configurable rather than silently universal;
- relaxation behavior is approved;
- examples cover split groups, combined lessons, difficult-subject load, availability, rooms, and infeasibility;
- the requirements owner approves the catalog version.

