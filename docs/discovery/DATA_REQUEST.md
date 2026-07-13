# Discovery Data Request

## Purpose

Representative artifacts are needed to validate terminology, rules, import expectations, and quality criteria. The repository must contain only sanitized examples that are safe to retain and share with authorized contributors.

## Requested artifacts

| Artifact | Minimum useful content | Why it is needed |
| --- | --- | --- |
| Completed timetable | At least one normal week with class, teacher, room, day, and period relationships preserved. | Validate views, conflicts, patterns, and output expectations. |
| Curriculum or teaching plan | Subject requirements and weekly counts for representative classes and groups. | Validate lesson-demand modeling. |
| Teacher assignment table | Stable pseudonymous teacher identifiers mapped to subjects and classes or groups. | Validate teacher-resource relationships. |
| Availability example | Recurring unavailable and preferred slots for several resources. | Distinguish hard and soft time constraints. |
| Classroom list | Pseudonymous room identifiers, capacity bands, and required capabilities. | Validate room constraints. |
| School-day definition | Days, shifts, periods, bell times, and known calendar variations. | Validate the time model. |
| Rule or preference list | Written policies and recurring informal rules used by the scheduler. | Seed the Stage 2 constraint catalog. |
| Revision example | Two versions of one timetable with a short reason for each change. | Understand review and maintenance workflows. |
| Impossible or difficult case | A sanitized past situation that required negotiation or rule relaxation. | Validate diagnostics and trade-off handling. |

## Sanitization requirements

Before an artifact enters the repository:

- replace teacher and staff names with stable identifiers such as `T001`;
- remove student names, IDs, contact details, and attendance data;
- replace sensitive room or building labels if they reveal protected information;
- remove author names and hidden metadata from office files;
- remove comments, revision history, external links, and embedded credentials;
- preserve relationships and scheduling patterns needed for analysis;
- record who authorized the sanitized artifact and its permitted use outside the file itself.

Do not rely on visual masking alone. Hidden worksheets, document properties, comments, and prior revisions must also be inspected.

## Intake record

For every accepted artifact, record:

| Field | Description |
| --- | --- |
| Artifact ID | Stable discovery identifier, such as `SRC-001`. |
| Description | What the artifact represents. |
| Period represented | Academic period and whether it is typical. |
| Evidence level | Reported or observed. |
| Sanitization reviewer | Role or approved pseudonymous identifier. |
| Permission | Approved project uses and sharing limits. |
| Repository location | Path to the sanitized copy, if committed. |
| Known limitations | Missing fields, artificial replacements, or unusual conditions. |

## Initial dataset coverage

The first representative package should include at least:

- one lower-complexity class without split groups;
- one class with at least one split-group subject;
- one teacher with restricted availability;
- one specialized classroom requirement;
- one difficult-subject balancing example;
- one fixed lesson or school event;
- one known preference conflict.

This is a coverage target, not a claim about the final data model.

