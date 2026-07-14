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
