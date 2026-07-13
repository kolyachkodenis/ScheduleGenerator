# Timetable Quality Criteria

## Status

- **Evidence level:** Hypothesis
- **Targets:** Not yet approved
- **Validation owner:** Unassigned school-side requirements owner

No metric in this document is a product requirement until its definition, scope, priority, and target are approved.

## Validity metrics

These are candidates for hard acceptance gates:

| Metric | Candidate definition | Proposed target |
| --- | --- | --- |
| Resource conflicts | Assignments in which a class, group, teacher, or classroom is required in more than one lesson at the same time. | 0 |
| Missing required lessons | Curriculum-required lessons that are not assigned. | 0 |
| Excess assigned lessons | Lessons assigned beyond an approved curriculum requirement. | 0 |
| Availability violations | Assignments placed in a resource's prohibited time slot. | 0 |
| Room requirement violations | Lessons assigned to rooms that do not meet hard capacity or capability requirements. | 0 |
| Daily-limit violations | Class or teacher daily counts outside an approved hard limit. | 0 |

Discovery must determine which daily limits and room conditions are truly hard.

## Quality metrics

These are candidates for scored preferences:

| Metric | Candidate measurement | Questions requiring approval |
| --- | --- | --- |
| Difficult-subject load | Daily sum or count of subject workload scores for each class. | Who assigns scores? Is the limit grade-specific? |
| Class gaps | Empty assignable periods between a class's first and last lesson. | Are any gaps allowed? Does lunch count? |
| Teacher gaps | Empty assignable periods between a teacher's first and last lesson. | Is total count or longest gap more important? |
| Weekly subject spread | Distance and balance between lessons of the same subject. | Are consecutive days or long gaps undesirable? |
| Daily lesson balance | Difference between a class's heaviest and lightest teaching days. | Are some days intentionally shorter? |
| Edge-period use | Undesirable first or last lesson assignments. | Which grades, teachers, or subjects are affected? |
| Consecutive lessons | Runs of lessons for a class or teacher. | What are preferred and maximum run lengths? |
| Classroom changes | Number of room transitions for a class or teacher. | Does building travel require a separate metric? |
| Preference satisfaction | Weighted share of explicit teacher or school preferences met. | Who approves weights and overrides? |

## Operational metrics

Candidate product-success measurements include:

- scheduler active time from accepted inputs to reviewable candidate;
- elapsed generation time for a representative dataset;
- number of manual edits before approval;
- number of review cycles;
- number and severity of defects found after publication;
- time required to produce a corrected version;
- percentage of solver failures with actionable diagnostics.

## Baseline and target process

1. Measure the current process on at least one representative timetable cycle.
2. Agree on precise metric definitions and exclusions.
3. Record baseline values with evidence references.
4. Assign each preference a priority before assigning numerical weights.
5. Set MVP targets with the requirements owner.
6. Test targets against sanitized historical examples.
7. Revisit weights during the pilot without changing hard validity rules silently.

## Quality review record

For each reviewed candidate, capture:

- dataset and timetable version;
- generator version, configuration, seed, and time limit;
- hard-validity result;
- each quality metric and total score;
- manual edits made before approval;
- reviewer decision and the reasons for rejection or acceptance.

