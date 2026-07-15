# Representative Timetable Sample Analysis

## Source record

| Field | Value |
| --- | --- |
| Artifact ID | `SRC-001` |
| Description | Completed weekly class timetable supplied as a DOCX file |
| Received | 2026-07-15 |
| Evidence level | Observed |
| Repository location | Not committed; retained outside the repository pending sanitization and permission review |
| Known limitations | No teachers, classrooms, bell times, academic period, or explicit subgroup definitions |

The source contains no visible student records or teacher names. Its document metadata,
retention permission, and authorization for wider sharing have not been approved, so the
original file must not be added to the repository.

## Observed structure

The timetable represents a five-day teaching week for 18 class sections across grades 5
through 11:

- grades 10 and 11 have sections A and B;
- grade 9 has sections A, B, and C;
- grade 8 has sections A and B;
- grades 5, 6, and 7 have sections A, B, and C;
- days contain up to seven numbered lesson periods;
- younger classes generally have fewer lessons than older classes;
- some classes have an empty first period;
- grades 1 through 4 are not represented.

The document uses separate table blocks for older, middle, and younger classes. Some table
rows cross page boundaries. Weekday labels are explicit only in the older-class block; in
the other blocks, Monday through Friday are implied by row order.

## Split and parallel lessons

Many period entries contain slash-separated subjects or repeated language labels. The
patterns include:

- different foreign languages taught concurrently;
- informatics and foreign-language groups sharing one class period;
- informatics and practical-training groups taught concurrently;
- profile combinations involving mathematics, biology, physics, and chemistry.

These entries are evidence that a class period cannot always be represented by one subject
assignment. The domain model must support multiple concurrent assignments for distinct
groups belonging to the same class. Each assignment may require its own teacher and room.

The sample does not define the groups or identify which pupils belong to them. It also does
not establish whether groups from different partitions may be scheduled concurrently.
Those semantics remain unconfirmed.

## Daily workload observations

The timetable includes days with several mathematics, physics, chemistry, or biology
entries. This supports the need for a daily workload metric, but it does not establish:

- which subjects the school considers difficult for each grade;
- the relative difficulty weight of each subject;
- whether a split period contributes the maximum, average, or group-specific weight;
- the acceptable daily limit;
- whether consecutive difficult lessons require an additional penalty.

Difficulty thresholds and weights must therefore remain configurable and require approval
from the school-side requirements owner.

## Source-data quality

The sample is useful as a realistic import test because it contains common source-data
issues:

- inconsistent abbreviations, punctuation, and whitespace;
- multiple spellings for the same subject;
- typographical errors;
- missing paragraph breaks that join adjacent lesson numbers;
- blank periods represented inconsistently;
- page layout carrying meaning that is absent from the cell text;
- slash notation whose semantics cannot be inferred safely without school input.

An importer must not silently convert these values into scheduling data. It should provide
a normalization preview, identify ambiguous cells, and require confirmation before saving.

## Confirmed model implications

The observed artifact strengthens the need for the following capabilities:

1. Variable daily lesson limits by class or grade.
2. Explicit empty or unavailable class slots, including an empty first period.
3. Class partitions and concurrent subgroup assignments.
4. Stable subject identifiers with separately normalized display labels.
5. Grade-specific subject difficulty configuration.
6. Import diagnostics that preserve the source row, column, and original value.

The sample does not provide evidence for teacher conflicts, room conflicts, shifts,
specialized-room requirements, fixed events, alternating weeks, or calendar exceptions.

## Follow-up data required

Before this sample can become a pilot dataset, collect:

- the curriculum and expected weekly lesson counts;
- pseudonymous teacher assignments and availability;
- classrooms and required capabilities;
- the bell schedule and shift definitions;
- explicit subgroup definitions for every slash-separated period;
- approved subject difficulty weights and daily limits;
- confirmation that the represented week is typical;
- a sanitized, authorized copy and a completed intake record.

Until those items are available, `SRC-001` is discovery evidence only and must not be used
as a source of truth for solver acceptance tests.
