# Constraint Test Coverage

## Status meanings

- `Automated`: implemented by core 0.2.0 and protected by automated tests.
- `Deferred`: present in the catalog but not implemented in core 0.2.0; discovery or model work is still required.

## Hard constraints

| Constraint | Status | Primary verification |
| --- | --- | --- |
| HC-001 | Automated | Exact occurrence expansion and model selection tests. |
| HC-002 | Automated | Independent class collision test. |
| HC-003 | Automated | Independent group collision test. |
| HC-004 | Automated | Independent teacher collision test. |
| HC-005 | Automated | Independent classroom collision test. |
| HC-006 | Automated | Shift-filtered candidate test. |
| HC-007 | Automated | Teacher-unavailability candidate test and impossible overlay. |
| HC-008 | Automated | Classroom-unavailability candidate test. |
| HC-009 | Automated | Fixed-candidate and reference-placement tests. |
| HC-010 | Automated | Eligible-teacher candidate test. |
| HC-011 | Automated | Required-capability candidate test. |
| HC-012 | Automated | Capacity candidate test. |
| HC-013 | Automated | Split-group atom disjointness and coverage test. |
| HC-014 | Automated | Cohort member-atom expansion test. |
| HC-015 | Automated | Isolated infeasible daily class limit test. |
| HC-016 | Automated | Isolated infeasible daily teacher limit test. |
| HC-017 | Automated | Consecutive block candidate property test. |
| HC-018 | Deferred | Prior locked assignments are not part of input schema 0.1.0. |

## Soft constraints

| Constraint | Status | Primary verification |
| --- | --- | --- |
| SC-001 | Automated | Exact difficult-load raw and weighted penalty test. |
| SC-002 | Automated | Exact class daily-load spread penalty test. |
| SC-003 | Automated | Exact internal class-gap penalty test. |
| SC-004 | Automated | Exact internal teacher-gap penalty test. |
| SC-005 | Automated | Exact same-day subject-spread proxy penalty test. |
| SC-006 | Deferred | Separate repeated-subject semantics are not implemented. |
| SC-007 | Automated | Exact non-preferred teacher-slot penalty test. |
| SC-008 | Deferred | Edge-period policy is not represented in schema 0.1.0. |
| SC-009 | Deferred | Preferred class run length is not represented. |
| SC-010 | Deferred | Preferred teacher run length is not represented. |
| SC-011 | Deferred | Home-room and movement policy are not represented. |
| SC-012 | Deferred | Building and travel data are not represented. |
| SC-013 | Deferred | Subject time-window policy is not represented. |
| SC-014 | Deferred | Prior unlocked assignments are not provided to generation. |
| SC-015 | Deferred | Teacher weekly-load preference is not represented. |
| SC-016 | Deferred | Compact teacher-day policy is not represented. |
| SC-017 | Deferred | Parallel-group preference semantics await discovery. |
| SC-018 | Deferred | Optional room-suitability ranking is not represented. |

The repository check compares this matrix with the catalog so every catalog ID has exactly one declared coverage state.

