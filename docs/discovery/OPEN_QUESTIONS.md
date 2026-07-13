# Open Discovery Questions

## Status values

- `Blocking`: Stage 1 cannot be approved without an answer.
- `Open`: Important, but may be deferred with an explicit scope decision.
- `Resolved`: Answer and evidence have been recorded.
- `Out of scope`: Explicitly excluded from the current product boundary.

## Ownership and scope

| ID | Status | Question | Decision owner |
| --- | --- | --- | --- |
| DQ-001 | Blocking | Who is the school-side requirements owner authorized to approve Stage 1? | Repository owner |
| DQ-002 | Blocking | Which school, grades, academic term, and scheduling unit will the first representative dataset cover? | Requirements owner |
| DQ-003 | Open | Is the product intended for one specific school first or for configurable use across schools from the MVP? | Product owner |

## Time structure

| ID | Status | Question | Decision owner |
| --- | --- | --- | --- |
| DQ-010 | Blocking | Which weekdays, shifts, and lesson periods are used? | Requirements owner |
| DQ-011 | Blocking | Do bell times differ by day, grade, building, or shift? | Requirements owner |
| DQ-012 | Open | Are alternating weeks or term-specific week patterns required in the MVP? | Product owner |
| DQ-013 | Open | How are shortened days, assemblies, and one-off calendar events represented? | Scheduler |

## Classes and teaching patterns

| ID | Status | Question | Decision owner |
| --- | --- | --- | --- |
| DQ-020 | Blocking | How are classes divided into groups, and can membership patterns differ by subject? | Requirements owner |
| DQ-021 | Blocking | Which combined-class or combined-group lessons must be supported? | Requirements owner |
| DQ-022 | Open | Must one lesson support multiple teachers or assistants? | Product owner |
| DQ-023 | Open | Are individual student selections required, or are class and group assignments sufficient? | Product owner |

## Rules and quality

| ID | Status | Question | Decision owner |
| --- | --- | --- | --- |
| DQ-030 | Blocking | Which rules are legally or operationally mandatory and therefore hard constraints? | Requirements owner |
| DQ-031 | Blocking | How is subject difficulty defined, and does it vary by grade? | Requirements owner |
| DQ-032 | Blocking | What daily difficult-subject load is acceptable? | Requirements owner |
| DQ-033 | Blocking | Which class and teacher gaps are prohibited or merely undesirable? | Requirements owner |
| DQ-034 | Open | How should conflicting teacher preferences be prioritized? | Requirements owner |
| DQ-035 | Open | Which constraints may be relaxed when no valid timetable exists? | Requirements owner |

## Inputs and outputs

| ID | Status | Question | Decision owner |
| --- | --- | --- | --- |
| DQ-040 | Blocking | What are the authoritative input formats and owners? | Scheduler |
| DQ-041 | Blocking | Which sanitized examples may be used for development and tests? | Requirements owner |
| DQ-042 | Blocking | Which timetable views and export layouts are mandatory? | Requirements owner |
| DQ-043 | Open | Where is the approved timetable published today? | Scheduler |

## Operations and success

| ID | Status | Question | Decision owner |
| --- | --- | --- | --- |
| DQ-050 | Blocking | What is the current active effort and elapsed time for one timetable cycle? | Scheduler |
| DQ-051 | Blocking | What solver wait time is acceptable for initial generation and later edits? | Requirements owner |
| DQ-052 | Blocking | Which measurable outcome makes the MVP successful? | Product owner |
| DQ-053 | Open | How often is an approved timetable revised, and what response time is expected? | Scheduler |

## Resolution format

When resolving a question, add a note below its table using this format:

```text
DQ-NNN — Resolved YYYY-MM-DD
Decision: ...
Evidence: interview or artifact reference
Approved by: role or GitHub handle
Impact: affected use cases, constraints, or scope
```

Do not mark a question resolved based only on an undocumented assumption.
