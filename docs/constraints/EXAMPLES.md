# Constraint Examples

These synthetic examples define intended rule semantics without using real school data. Names such as `Class-7A`, `T-Math`, and `Room-Lab` are test identifiers.

## CX-001: Valid independent lessons

At Monday period 1, `Class-7A` has Mathematics with `T-Math` in `Room-201`, while `Class-8A` has History with `T-History` in `Room-105`.

**Expected:** No non-overlap violation because all participating resources are distinct.

**Rules:** HC-002, HC-004, HC-005.

## CX-002: Teacher collision

At Monday period 2, `T-Math` is assigned to both `Class-7A` and `Class-8A`.

**Expected:** The timetable is infeasible under HC-004, even if the lessons use different rooms.

## CX-003: Split groups in parallel

`Class-7A` is partitioned into non-overlapping groups `7A-L1` and `7A-L2`. Both groups have Language at Tuesday period 3 with different teachers and rooms.

**Expected:** The assignments may coexist when the partition is approved. HC-002 must not treat a valid split as a whole-class collision; HC-003, HC-004, HC-005, and HC-013 still apply.

## CX-004: Invalid overlapping groups

Two groups scheduled concurrently share at least one student according to the approved membership model.

**Expected:** The timetable is infeasible under HC-003 and cannot be repaired by assigning different rooms or teachers.

## CX-005: Combined lesson

`Class-8A` and `Class-8B` form cohort `Cohort-8-Assembly` for one lesson with `T-Assembly` in `Room-Hall`.

**Expected:** Both classes are occupied for the slot, the teacher and hall are occupied once, and the assignment is valid only if the cohort definition permits the combination.

**Rules:** HC-002, HC-004, HC-005, HC-014.

## CX-006: Specialized room conflict

A Chemistry laboratory lesson requires capability `chemistry-lab`. `Room-204` is available but lacks the capability; `Room-Lab` has it but is already occupied.

**Expected:** `Room-204` is invalid under HC-011 and `Room-Lab` cannot be double-booked under HC-005. The requirement has no feasible room in this slot.

## CX-007: Teacher unavailable

`T-Physics` is marked hard-unavailable on Wednesday period 1 but is assigned a Physics lesson then.

**Expected:** The timetable is infeasible under HC-007. A mere preference would instead be modeled and scored under SC-007.

## CX-008: Required double lesson

A requirement declares a block length of two. It is placed at Thursday periods 3 and 4, which are consecutive compatible periods.

**Expected:** HC-017 is satisfied. Placement at periods 3 and 5, on different days, or across a disallowed break violates the rule.

## CX-009: Difficult-subject overload

For one class, Mathematics, Physics, and Chemistry each have workload score 2. Their daily configured target is 4, and all three are assigned on Monday.

**Expected:** The timetable remains feasible if the rule is soft, but SC-001 produces a penalty for 2 points above the target. The exact penalty curve remains configurable.

## CX-010: Class gap

`Class-7A` has lessons in periods 1, 2, 4, and 5, with period 3 assignable and empty.

**Expected:** SC-003 counts one gap period unless period 3 is defined as a non-assignable lunch or break.

## CX-011: Subject spread trade-off

Four weekly Mathematics lessons can be placed either on four separate days or as two occurrences on Monday and two on Tuesday.

**Expected:** Subject-spread and repeated-subject penalties favor the first option unless block requirements or higher-priority constraints make the second preferable.

**Rules:** SC-005, SC-006.

## CX-012: Locked partial regeneration

An accepted Friday period 2 lesson is locked before regeneration. The solver finds a lower-penalty timetable only by moving it.

**Expected:** The move is prohibited by HC-018. Solver quality cannot outweigh a lock.

## CX-013: Conflicting fixed lessons

Two fixed lessons require the same teacher at the same time.

**Expected:** No feasible timetable exists under HC-004 and HC-009. The system reports both fixed assignments and does not silently move either one.

## CX-014: Stability versus quality

During regeneration, moving two unlocked lessons removes five teacher gaps but changes an already reviewed class schedule.

**Expected:** SC-004 and SC-014 create a measurable trade-off resolved by approved priority tiers and weights. The quality report shows both effects.

## Example acceptance template

Each future example should state:

- sanitized input facts;
- applicable constraint IDs;
- expected feasibility;
- expected violations or penalty direction;
- expected diagnostic details;
- evidence source and approval status.
