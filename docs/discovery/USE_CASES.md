# Discovery Use Cases

## Status

- **Evidence level:** Hypothesis
- **Validation owner:** Unassigned school-side requirements owner
- **Last updated:** 2026-07-13

The use cases describe outcomes, not screens or implementation technologies.

## UC-01: Define the scheduling period

**Primary actor:** Scheduler

**Outcome:** The system has an approved set of school days, shifts, lesson periods, and calendar exceptions for the timetable period.

**Questions to validate:** Are different bell schedules used by grade, day, building, or shift? Are alternating weeks needed?

## UC-02: Register scheduling resources

**Primary actor:** Scheduler or data provider

**Outcome:** Classes, groups, teachers, subjects, and classrooms are complete and internally consistent.

**Questions to validate:** Which systems are authoritative? Are co-teachers, assistant teachers, or roomless lessons common?

## UC-03: Define curriculum requirements

**Primary actor:** Scheduler or curriculum owner

**Outcome:** Every class or group has an approved number of weekly lessons for each subject and an assigned teacher or eligible teacher set.

**Questions to validate:** Can requirements be expressed over more than one week? How are double lessons represented?

## UC-04: Record availability and fixed assignments

**Primary actor:** Scheduler

**Outcome:** Resource unavailability and genuinely fixed lessons are recorded with their authority and reason.

**Questions to validate:** Which constraints are contractual, operational, or merely preferred? Who may override them?

## UC-05: Configure quality preferences

**Primary actor:** Scheduler and requirements owner

**Outcome:** Difficult-subject load, gaps, daily balance, and other preferences have agreed priorities.

**Questions to validate:** How is subject difficulty determined? Do priorities differ by age group?

## UC-06: Validate scheduling inputs

**Primary actor:** Scheduler

**Outcome:** Missing, contradictory, or obviously infeasible data is reported before generation, with enough detail to correct it.

**Questions to validate:** Which errors should block generation, and which warnings may be accepted?

## UC-07: Generate timetable alternatives

**Primary actor:** Scheduler

**Outcome:** The scheduler receives one or more valid candidates, their quality scores, and a summary of unmet preferences within an acceptable time.

**Questions to validate:** How many alternatives are useful? What wait time is acceptable during initial generation and later refinement?

## UC-08: Diagnose an unsatisfiable problem

**Primary actor:** Scheduler

**Outcome:** When no valid timetable exists, the scheduler receives actionable evidence about conflicting inputs or rules.

**Questions to validate:** What level of explanation is sufficient to negotiate a change?

## UC-09: Review and adjust a candidate

**Primary actor:** Scheduler

**Outcome:** The scheduler can compare views, make manual changes, and immediately see conflicts and quality impact.

**Questions to validate:** Which views and comparisons are used during review? Which changes must be locked before regeneration?

## UC-10: Approve and publish a timetable

**Primary actor:** School administrator or delegated approver

**Outcome:** An identified timetable version is approved and exported or published without exposing drafts.

**Questions to validate:** What constitutes approval, and which output formats are mandatory?

## UC-11: Revise an approved timetable

**Primary actor:** Scheduler

**Outcome:** A correction produces a new traceable version while the prior approved version remains recoverable.

**Questions to validate:** How frequently do revisions occur, and how quickly must readers receive them?

## Use-case approval checklist

For each use case, discovery must establish:

- whether it occurs in the real process;
- its frequency and business importance;
- the responsible actor and approver;
- required inputs and outputs;
- failure and exception paths;
- whether it belongs in the MVP;
- at least one sanitized example.

