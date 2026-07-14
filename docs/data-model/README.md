# Data Model

## Status

- **Roadmap stage:** Stage 3, in progress
- **Schema version:** 0.1.0
- **Evidence:** Draft model based on the current constraint catalog
- **Approval owner:** Unassigned school-side requirements owner

The model is deliberately solver-independent and storage-independent. It represents the information needed to validate inputs and build scheduling problems; it is not a production database schema.

## Artifacts

- [`school-dataset.schema.json`](../../schemas/school-dataset.schema.json): structural JSON Schema using Draft 2020-12.
- [`small-school.json`](../../examples/small-school.json): synthetic demonstration dataset.
- [`validate_dataset.py`](../../scripts/validate_dataset.py): schema and semantic validation command.
- [ADR 0002](../adr/0002-versioned-json-datasets.md): rationale for the prototype exchange format.

## Conceptual model

```mermaid
erDiagram
    SCHOOL ||--|| ACADEMIC_PERIOD : configures
    ACADEMIC_PERIOD ||--o{ DAY : contains
    ACADEMIC_PERIOD ||--o{ SHIFT : contains
    SHIFT }o--o{ PERIOD : permits
    CLASS }o--|| SHIFT : follows
    CLASS ||--o{ GROUP_PARTITION : defines
    GROUP_PARTITION ||--o{ GROUP : contains
    COHORT }o--o{ CLASS : combines
    COHORT }o--o{ GROUP : combines
    SUBJECT ||--o{ CURRICULUM_REQUIREMENT : requires
    CLASS ||--o{ CURRICULUM_REQUIREMENT : receives
    GROUP ||--o{ CURRICULUM_REQUIREMENT : receives
    COHORT ||--o{ CURRICULUM_REQUIREMENT : receives
    TEACHER }o--o{ CURRICULUM_REQUIREMENT : eligible_for
    CLASSROOM }o--o{ CURRICULUM_REQUIREMENT : can_host
    CURRICULUM_REQUIREMENT ||--o{ FIXED_LESSON : fixes
    TIMETABLE_VERSION ||--o{ LESSON_ASSIGNMENT : contains
    CURRICULUM_REQUIREMENT ||--o{ LESSON_ASSIGNMENT : fulfills
```

## Aggregate structure

One dataset contains:

- school identity and timezone;
- one academic period with teaching days, periods, and shifts;
- subjects, teachers, classrooms, classes, partitions, groups, and cohorts;
- curriculum requirements defining lesson demand;
- hard unavailability and soft time preferences;
- fixed lesson placements;
- configurable constraint policies and soft-constraint weights;
- optional timetable versions with assignments and change history.

## Identity and references

All records use stable machine IDs matching `^[a-z][a-z0-9_-]*$`. Labels are display values and may change without breaking references. References use a typed object where different resource collections can be targeted.

The JSON Schema validates shapes and primitive ranges. The semantic validator additionally verifies:

- uniqueness of IDs within every collection;
- existence and type of references;
- class-to-shift and group-to-partition consistency;
- group sizes within their class and complete partition totals;
- qualified subjects and eligible teachers;
- valid day and period slot references;
- curriculum counts divisible by their block length;
- fixed occurrence indices and placements;
- known constraint IDs in policy configuration;
- timetable version and assignment references.

## Time model

A `day` is a recurring teaching day in the academic period. A `period` defines an ordinal lesson position and optional clock times. A `shift` selects the periods available to its classes. A time slot is a `day_id` and `period_id` pair.

Local access control is stored separately from school reference data. `app_users` contains the username, password hash, role, enabled state, lockout counters, and security timestamps. `user_sessions` stores only hashed, expiring, revocable session tokens. `audit_events` records an actor, action, target, outcome, selected non-secret metadata, and timestamp.

Calendar exceptions and alternating-week patterns are intentionally not modeled in version 0.1.0 because discovery has not confirmed their MVP semantics.

## Student grouping without personal data

The model stores class and group sizes, not student identities. A `group_partition` declares one way a class is split, such as a language partition. Groups belonging to a complete partition must sum to the class size.

This representation can validate capacity and partition totals but cannot prove that two groups from different partitions have no students in common. If real scheduling needs cross-partition concurrency, Stage 1 must determine whether anonymous membership sets or an explicit compatibility relation is required.

## Curriculum requirements

A curriculum requirement connects one class, group, or cohort to:

- a subject;
- a number of lesson periods per week;
- a block length;
- one or more eligible teachers;
- required classroom capabilities;
- optional allowed classroom IDs.

For schema version 0.1.0, `weekly_lessons` counts lesson periods. It must be divisible by `block_length`; the quotient is the number of occurrences to schedule.

## Availability and preferences

`resource_availability` records hard-unavailable slots and soft-preferred slots for teachers, classrooms, classes, and groups. School policies hold daily limits, difficult-subject targets, and enabled soft-constraint weights.

Rules remain identified by the stable IDs in the [constraint catalog](../constraints/CATALOG.md). Configuration does not redefine their meaning.

## Timetable versions and history

The schema supports immutable timetable-version records with status, creation time, generation metadata, assignments, and an append-only change summary. A future persistence model may normalize these records, but it must preserve reproducibility and lineage.

The synthetic example has no generated timetable yet, so its `timetable_versions` collection is empty.

## Validation command

Install the development dependency and validate the example:

```powershell
python -m pip install --requirement requirements-dev.txt
python scripts/validate_dataset.py --require-schema examples/small-school.json
```

Without `jsonschema`, the command still performs JSON parsing and semantic checks, but `--require-schema` intentionally fails. CI always requires full schema validation.

## Open design decisions

- anonymous group membership versus partition compatibility;
- multi-teacher and multi-room lessons;
- calendar exceptions and alternating weeks;
- teacher eligibility versus fixed teacher assignment;
- grade-specific subject workload values;
- building locations and travel time;
- the boundary between dataset policy and generation-run configuration;
- external identity-provider integration and long-term audit retention policy.

These decisions must be resolved with discovery evidence before Stage 3 is marked complete.
