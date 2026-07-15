# Rule Catalog

## Interpretation

All entries are currently `Draft`. Cardinalities, thresholds, applicability, and exceptions must come from validated school data. A hard constraint defines feasibility; a soft constraint contributes a non-negative penalty to timetable quality.

## Hard constraints

| ID | Name | Rule statement | Primary scope | Required inputs | Violation | Status |
| --- | --- | --- | --- | --- | --- | --- |
| HC-001 | Required lesson coverage | Every curriculum requirement must receive exactly its approved number of lesson occurrences in the timetable period. | Curriculum requirement | Required count, period | Assigned count differs from required count. | Draft |
| HC-002 | Class non-overlap | A class must not attend more than one incompatible lesson in the same time slot. | Class, time slot | Lesson participants | Concurrent assignments exist. | Draft |
| HC-003 | Group non-overlap | A student group must not attend more than one incompatible lesson in the same time slot. | Group, time slot | Group membership pattern, lesson participants | Concurrent assignments exist. | Draft |
| HC-004 | Teacher non-overlap | A teacher must not teach more than one incompatible lesson in the same time slot. | Teacher, time slot | Teacher assignments | Concurrent assignments exist. | Draft |
| HC-005 | Classroom non-overlap | A classroom must not host more than one lesson in the same time slot. | Classroom, time slot | Room assignments | Concurrent assignments exist. | Draft |
| HC-006 | Allowed time slot | A lesson may be assigned only to a time slot enabled for its class or group and scheduling period. | Lesson, time slot | Calendar, shift, class availability | Lesson uses a prohibited slot. | Draft |
| HC-007 | Teacher availability | A teacher may be assigned only when marked available for mandatory purposes. | Teacher, time slot | Teacher availability | Assignment occurs during hard unavailability. | Draft |
| HC-008 | Classroom availability | A classroom may be assigned only when operationally available. | Classroom, time slot | Room availability | Assignment occurs during hard unavailability. | Draft |
| HC-009 | Fixed lesson placement | A fixed lesson must retain every placement attribute declared fixed. | Lesson | Fixed day, period, teacher, or room fields | An assignment differs from a fixed value. | Draft |
| HC-010 | Qualified teacher | Every lesson must use the required teacher or a teacher approved as eligible for that requirement. | Lesson, teacher | Teaching assignment or eligibility | Assigned teacher is not eligible. | Draft |
| HC-011 | Required classroom capability | A lesson must use a classroom with every mandatory capability. | Lesson, classroom | Required and provided capabilities | At least one required capability is absent. | Draft |
| HC-012 | Classroom capacity | A lesson must not exceed a hard classroom capacity limit when capacity is applicable. | Lesson, classroom | Participant count or band, room capacity | Participants exceed capacity. | Draft |
| HC-013 | Split-group integrity | Simultaneous split-group lessons must use non-overlapping groups that belong to the intended class partition. | Class, group, time slot | Group membership and partition | Groups overlap or do not form an allowed partition. | Draft |
| HC-014 | Combined-lesson integrity | A combined lesson must include exactly the approved classes or groups and required teaching resources. | Cohort, lesson | Cohort definition, teachers | Participants or resources differ from the approved combination. | Draft |
| HC-015 | Daily class limit | A class or group must not exceed an approved hard number of lessons in a school day. | Class or group, day | Daily limit | Assigned count exceeds the limit. | Draft |
| HC-016 | Daily teacher limit | A teacher must not exceed a contractual or approved hard number of lessons in a school day. | Teacher, day | Daily limit | Assigned count exceeds the limit. | Draft |
| HC-017 | Consecutive block integrity | A requirement declared as a fixed-length block must occupy consecutive compatible time slots on the same day. | Requirement, day | Block length, slot sequence | Block is split, incomplete, or crosses an invalid boundary. | Draft |
| HC-018 | Locked assignment preservation | A locked lesson must retain its locked placement during partial regeneration. | Lesson | Lock fields and values | A locked value changes. | Draft |

## Soft constraints

| ID | Name | Preference statement | Primary scope | Candidate penalty unit | Status |
| --- | --- | --- | --- | --- | --- |
| SC-001 | Difficult-subject daily limit | Keep each class's daily difficult-subject workload at or below its configured target. | Class, day | Workload points above target | Draft |
| SC-002 | Balanced daily class load | Distribute a class's lessons across teaching days without avoidable heavy and light extremes. | Class, week | Deviation from target daily load | Draft |
| SC-003 | Avoid class gaps | Minimize unused assignable periods between a class's first and last lesson. | Class, day | Gap periods | Draft |
| SC-004 | Avoid teacher gaps | Minimize unused assignable periods between a teacher's first and last lesson. | Teacher, day | Gap periods, optionally weighted by length | Draft |
| SC-005 | Spread subject lessons | Distribute occurrences of the same subject across suitable days. | Class and subject, week | Too-close or too-distant occurrence pairs | Draft |
| SC-006 | Avoid repeated subject in one day | Avoid multiple occurrences of a subject for a class on one day unless a block is requested. | Class and subject, day | Extra occurrences | Draft |
| SC-007 | Prefer teacher time slots | Prefer time slots explicitly requested by a teacher when they do not conflict with higher rules. | Teacher, time slot | Unsatisfied preference | Draft |
| SC-008 | Avoid undesirable edge periods | Avoid selected first or last periods for configured subjects, classes, or teachers. | Resource, day | Undesirable edge assignment | Draft |
| SC-009 | Limit consecutive class lessons | Avoid class lesson runs longer than a configured target. | Class, day | Periods above target run length | Draft |
| SC-010 | Limit consecutive teacher lessons | Avoid teacher lesson runs longer than a configured target. | Teacher, day | Periods above target run length | Draft |
| SC-011 | Reduce classroom changes | Keep a class in the same room when movement has no educational benefit. | Class, adjacent lessons | Avoidable room transition | Draft |
| SC-012 | Reduce teacher travel | Avoid room transitions that require insufficient travel time between buildings or zones. | Teacher, adjacent lessons | Transition cost by distance band | Draft |
| SC-013 | Prefer subject time window | Place configured subjects within pedagogically preferred parts of the day. | Subject, class, period | Distance from preferred window | Draft |
| SC-014 | Preserve timetable stability | During regeneration, minimize changes to previously accepted but unlocked assignments. | Existing timetable | Changed placement fields | Draft |
| SC-015 | Balance teacher weekly load | Distribute a teacher's lessons across working days according to configured preferences. | Teacher, week | Deviation from preferred daily load | Draft |
| SC-016 | Prefer compact teacher day | Avoid isolated first or last lessons and unnecessarily long on-site spans. | Teacher, day | Excess span or isolated lesson | Draft |
| SC-017 | Prefer parallel group alignment | Schedule compatible split groups concurrently when operationally preferred. | Class partition, time slot | Non-aligned group occurrence | Draft |
| SC-018 | Prefer classroom suitability | Among valid rooms, choose the room with the best matching optional capabilities or home-room preference. | Lesson, classroom | Suitability shortfall | Draft |
| SC-019 | Align related language subjects | Prefer scheduling a language and its corresponding literature subject on the same teaching day. | Class, related subject pair, day | Days containing only one subject from the pair | Draft |

## Rules requiring early validation

The following rules are structurally important and can substantially change the data model or solver design:

- HC-003 and HC-013: whether groups represent actual membership or only named partitions;
- HC-014: whether combined lessons can use multiple teachers or rooms;
- HC-017: whether consecutive blocks are mandatory, preferred, or both depending on the requirement;
- SC-001: how subject difficulty and daily load are measured by grade;
- SC-012: whether buildings and travel time belong in the MVP;
- SC-014: which placement fields count as a disruptive timetable change;
- SC-017: whether split groups must always be simultaneous.

Their unresolved discovery questions are tracked in [the discovery log](../discovery/OPEN_QUESTIONS.md).
