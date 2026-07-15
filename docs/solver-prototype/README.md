# Solver Prototype

## Status

- **Roadmap stage:** Stage 4, complete with synthetic evidence
- **Solver:** Google OR-Tools CP-SAT 9.15.6755
- **Input schema:** 0.1.0
- **Evidence:** Synthetic datasets only

The prototype demonstrates that the current domain model can be converted into a finite constraint-optimization problem. It is not the production scheduling core.

## Run the prototype

```powershell
python -m pip install --requirement requirements-dev.txt
$env:PYTHONPATH = "src"
python -m schedule_generator.prototype examples/small-school.json --output prototype-result.json --time-limit 10
```

The command validates its input, builds the model, solves within the time limit, independently verifies the selected assignments, and writes a JSON report.

## Implemented hard rules

| Rule | Prototype behavior |
| --- | --- |
| HC-001 | Creates the required number of occurrences and selects exactly one candidate for each. |
| HC-002/003 | Prevents overlapping atomic class or split-group participation. |
| HC-004 | Prevents teacher overlap. |
| HC-005 | Prevents classroom overlap. |
| HC-006 | Generates starts only within every participating class's shift. |
| HC-007/008 | Filters hard-unavailable teacher, classroom, class, and group slots. |
| HC-009 | Restricts fixed occurrences to their configured start, teacher, and room. |
| HC-010 | Generates candidates only for eligible, qualified teachers. |
| HC-011/012 | Generates candidates only for rooms satisfying capabilities and capacity. |
| HC-013 | Allows parallel groups in one complete partition while whole-class lessons occupy every group atom. |
| HC-014 | Expands a cohort to all member class and group atoms. |
| HC-015/016 | Enforces configured daily class and teacher limits. |
| HC-017 | Occupies consecutive periods for block requirements. |

HC-018 is deferred because schema version 0.1.0 contains no prior assignment input for partial regeneration.

## Implemented soft rules

- SC-001: difficult-subject daily overload for direct class and cohort requirements;
- SC-002: difference between the heaviest and lightest class day;
- SC-003: internal class gap periods;
- SC-004: internal teacher gap periods;
- SC-005: repeated same-subject starts on one day as a spread penalty;
- SC-007: assignments outside a teacher's explicitly preferred slots;
- SC-019: related language and literature lessons placed on different days.

Only configured rules contribute to the objective. Other catalog rules remain future work. Split-group workload is excluded from SC-001 and SC-005 until discovery defines whether parallel group lessons count once or separately for the parent class.

## Candidate model

For every requirement occurrence, preprocessing enumerates compatible combinations of:

- day and consecutive start periods;
- eligible teacher;
- classroom with sufficient capacity and capabilities.

Hard unavailability, fixed placements, and shift boundaries are applied before Boolean decision variables are created. If an occurrence has no candidate, the prototype returns `INPUT_INFEASIBLE` with affected constraint IDs instead of starting the solver.

## Result statuses

- `OPTIMAL`: a feasible timetable was found and the objective was proven best.
- `FEASIBLE`: a verified timetable was found before the time limit without proving optimality.
- `INFEASIBLE`: CP-SAT proved that the generated model has no solution.
- `UNKNOWN`: no feasible solution or proof was found before stopping.
- `INPUT_INFEASIBLE`: candidate preprocessing proved that one or more occurrences have no legal assignment.
- `INVALID_SOLUTION`: CP-SAT returned assignments that failed the independent validator.

## Reproducibility

The command accepts an integer seed and uses one search worker by default. The result records solver version, seed, time limit, status, objective, wall time, search statistics, assignments, penalties, diagnostics, and independent validation errors.

## Known limitations

- All classes currently need at most one complete group partition for correct atomic overlap behavior.
- Group workload semantics are not finalized.
- The weighted objective does not yet enforce lexicographic priority tiers.
- CP-SAT infeasibility after candidate generation returns only a general diagnostic; assumption-based conflict cores are future work.
- Calendar exceptions, alternating weeks, multi-teacher lessons, multi-room lessons, and locked regeneration are not modeled.
- Benchmarks use generated synthetic structures and cannot predict performance on real school data.

See [the preliminary benchmarks](BENCHMARKS.md) and [ADR 0003](../adr/0003-use-cp-sat-for-prototype.md).
