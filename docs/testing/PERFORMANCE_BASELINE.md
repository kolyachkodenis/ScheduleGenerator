# Scheduling Core Performance Baseline

## Environment

- **Date:** 2026-07-14
- **CPU:** AMD Ryzen 5 3550H
- **Operating system:** Windows 11 Pro 10.0.26200
- **Python:** 3.12.13
- **OR-Tools:** 9.15.6755
- **Seed:** 1
- **Search workers:** 1

## Results

| Classes | Status | End-to-end elapsed time | Python-tracked peak memory | Budget result |
| ---: | --- | ---: | ---: | --- |
| 2 | OPTIMAL | 2.140 s | 2.5 MiB | Pass |
| 6 | FEASIBLE | 15.472 s | 0.8 MiB | Pass |
| 11 | FEASIBLE | 15.896 s | 1.4 MiB | Pass |

The elapsed measurement includes dataset validation, candidate generation, model construction, solve time, result extraction, independent validation, and quality-report construction within the Python process. It excludes interpreter startup and dependency installation.

`tracemalloc` observes Python-managed allocations only. Native OR-Tools memory is not fully represented, so these figures are regression indicators rather than deployment capacity measurements.

The synthetic structures are defined by `scripts/benchmark_solver.py`. They do not represent a real school's complexity and must be replaced or supplemented after Stage 1 supplies approved representative data.

## Representative dataset optimization check

Measured on 2026-07-16 with `examples/small-school.json`, a 10-second search limit, seed 1, and one worker:

| Path | End-to-end elapsed time | Status | Assignments | Validation errors |
| --- | ---: | --- | ---: | ---: |
| Forced full-model search after constructive scheduling | 35.497 s | FEASIBLE | 562 | 0 |
| Large-model constructive fast path | 26.505 s | FEASIBLE | 562 | 0 |

The fast path reduced elapsed time by about 25% in this controlled comparison. It is used only when the model has at least 50,000 candidate decision variables, the requested search limit is at most 15 seconds, and constructive scheduling has already produced every required assignment. Longer optimization runs continue into the full CP-SAT model.

Candidate templates and participant-derived indexes are cached per requirement. The web interface defaults to four parallel search workers. Large interactive models use at least four workers for constructive preprocessing even when the full-model worker setting is lower.

The second optimization pass separates feasibility from quality optimization. With the web defaults (one alternative, four workers, and a 10-second limit), the same representative dataset completed in 14.085 seconds with 562 independently verified assignments and a quality penalty of 5,550. Related language alignment and same-day repetition retained the previous optimized raw penalties of 28 and 3 respectively.
