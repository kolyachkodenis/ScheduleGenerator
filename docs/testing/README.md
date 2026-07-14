# Testing Strategy

## Status

- **Roadmap stage:** Stage 6, complete for scheduling core 0.2.0
- **Frameworks:** Python `unittest` and Hypothesis 6.156.4
- **Regular CI:** functional, constraint, property, schema, model-size, documentation, and end-to-end CLI tests
- **Opt-in:** small, medium, and large solver performance budgets

Stage 6 completion applies to rules implemented by core 0.2.0. Catalog rules not yet implemented are explicitly marked `Deferred` in the [constraint coverage matrix](CONSTRAINT_COVERAGE.md). They cannot be considered implemented or move to automated status without corresponding tests.

## Test layers

| Layer | Purpose |
| --- | --- |
| Input schema | Reject malformed JSON structures and invalid primitive values. |
| Semantic input validation | Reject broken references, invalid partitions, unsuitable rooms, and unknown policies. |
| Candidate generation | Verify availability, shifts, fixed placements, eligibility, capacity, capabilities, groups, cohorts, and blocks. |
| Model constraints | Verify required coverage, non-overlap, and daily limits. |
| Independent solution validation | Check extracted assignments without trusting CP-SAT model construction. |
| Soft-penalty unit tests | Isolate each implemented soft rule with fully fixed synthetic lessons and assert exact raw and weighted penalties. |
| Property-based tests | Explore many key orders, group sizes, lesson counts, block lengths, and occurrence conflicts. |
| Reference scenarios | Preserve behavior-level expectations without snapshotting one arbitrary optimized timetable. |
| Scale regression | Limit model variable and constraint growth for the 11-class synthetic structure. |
| Performance budgets | Measure end-to-end generation time and Python-tracked peak memory for 2, 6, and 11 classes. |

## Regular test command

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover --start-directory tests --verbose
```

Regular CI skips the long solver performance suite but always checks the 11-class model-size budget.

## Performance test command

```powershell
$env:PYTHONPATH = "src"
$env:RUN_PERFORMANCE_TESTS = "1"
python -m unittest tests.test_performance.SolverPerformanceBudgetTests --verbose
```

Current provisional budgets are:

| Size | Solver time limit | End-to-end elapsed budget | Python-tracked peak memory |
| ---: | ---: | ---: | ---: |
| 2 classes | 5 seconds | 10 seconds | 512 MiB |
| 6 classes | 15 seconds | 25 seconds | 512 MiB |
| 11 classes | 15 seconds | 25 seconds | 512 MiB |

See the latest [local performance baseline](PERFORMANCE_BASELINE.md).

The memory figure comes from Python `tracemalloc` and does not include every native allocation inside OR-Tools. Before production capacity planning, add process-level resident-memory measurement on the deployment platform and replace these synthetic limits with representative school targets.

## Property-based tests

Hypothesis runs deterministic property suites with 25 examples per property and no timing deadline. Current properties establish that:

- dataset fingerprints do not depend on top-level mapping key order;
- complete partitions are valid exactly when group totals match class size;
- divisible weekly lesson counts expand into the exact occurrence count;
- any two distinct occurrences assigned to one class candidate produce a student conflict.

Property tests complement example tests; they do not replace explicit business scenarios.

## Reference scenario policy

Files under `tests/reference/` store synthetic input mutations and stable expectations. They intentionally avoid exact full-timetable snapshots because several equally valid assignments may have the same quality, and solver upgrades may choose another one.

Reference expectations should assert:

- accepted status classes;
- required assignment counts;
- fixed placements;
- independent validation results;
- quality-report structure;
- expected diagnostic codes for impossible inputs.

## Performance interpretation

Performance tests use one worker and a fixed seed. A `FEASIBLE` result satisfies the budget when independently valid even if optimality is not proven. A timeout with `UNKNOWN`, invalid result, or budget overrun fails the suite.

Synthetic performance tests are regression guards, not service-level objectives. Real targets remain blocked on the Stage 1 representative dataset.
