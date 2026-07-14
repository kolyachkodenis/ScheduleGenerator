# Reference Test Scenarios

Reference scenarios record stable behavioral expectations without snapshotting one exact optimized timetable. Exact assignments may change when valid optimization improvements are introduced, while hard invariants, fixed placements, result shape, and independent validation must remain stable.

- `small-school.expectations.json` defines the accepted result contract for the synthetic demonstration school.
- `teacher-unavailable.overlay.json` defines a reproducible impossible-input mutation used to test preprocessing diagnostics.

Every reference file contains synthetic data only.

