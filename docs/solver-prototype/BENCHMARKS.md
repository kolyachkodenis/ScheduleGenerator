# Preliminary Solver Benchmarks

These are synthetic engineering measurements, not product performance commitments. They measure CP-SAT wall time after model construction and exclude Python startup, JSON validation, candidate generation, and model-building time.

## Method

- **Date:** 2026-07-13
- **CPU:** AMD Ryzen 5 3550H
- **Operating system:** Windows 11 Pro 10.0.26200
- **Python:** 3.12.13
- **OR-Tools:** 9.15.6755
- **Seed:** 1
- **Search workers:** 1
- **Time limit:** 15 seconds per dataset

The generated datasets use five days, six periods, three subjects, one teacher per pair of classes for Mathematics and History, one shared Physical Education teacher, one general room per pair of classes, and one shared gym. Each class requires eight weekly lesson occurrences. The structure is intentionally reproducible but much simpler than a real school.

Run the same benchmark with:

```powershell
$env:PYTHONPATH = "src"
python scripts/benchmark_solver.py --sizes 2 6 12 --time-limit 15 --seed 1
```

<!-- BENCHMARK_RESULTS_START -->

| Classes | Assignments | Variables | Constraints | Status | Objective | Solver wall time | Independently verified |
| ---: | ---: | ---: | ---: | --- | ---: | ---: | --- |
| 2 | 16 | 986 | 1,042 | OPTIMAL | 8 | 1.479 s | Yes |
| 6 | 48 | 2,778 | 2,706 | FEASIBLE | 94 | 15.004 s | Yes |
| 12 | 96 | 5,466 | 5,202 | FEASIBLE | 447 | 15.017 s | Yes |

<!-- BENCHMARK_RESULTS_END -->

## Interpretation

- The 2-class model reached and proved the optimum.
- The 6-class and 11-class models found independently valid timetables but did not prove optimality within 15 seconds.
- Objective values are not comparable across different dataset sizes because larger datasets contain more penalty instances.
- Variable and constraint growth is moderate in this controlled structure, but room flexibility, groups, fixed lessons, and real preference interactions can increase search difficulty sharply.
- Production targets cannot be set until sanitized representative data and end-to-end timing are available.
