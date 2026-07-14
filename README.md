# ScheduleGenerator

A school timetable generator that automatically assigns lessons to days, time slots, and classrooms while accounting for classes, teachers, academic workload, and school policies.

## Project goal

Reduce the manual effort required to build school timetables and produce a valid, explainable result that remains easy to review and adjust.

The system should account for, among other things:

- the curriculum of every class;
- teacher availability and workload;
- classrooms, shifts, and allowed time slots;
- conflicts involving classes, teachers, and classrooms;
- daily lesson limits;
- balanced workload throughout the week;
- limits on the number of difficult subjects in one day;
- school and teacher preferences;
- manual adjustments followed by automatic validation.

## Status

The scheduling core, automated test suite, and local data-storage/import layer are implemented. Discovery with representative real school data remains in progress.

Project documentation:

- [Project charter](docs/PROJECT_CHARTER.md)
- [Roadmap](docs/ROADMAP.md)
- [Domain glossary](docs/GLOSSARY.md)
- [Scheduling-process discovery](docs/discovery/README.md)
- [Constraint catalog](docs/constraints/README.md)
- [Data model](docs/data-model/README.md)
- [Solver prototype](docs/solver-prototype/README.md)
- [Scheduling core](docs/scheduling-core/README.md)
- [Testing strategy](docs/testing/README.md)
- [School data storage and import](docs/data-import/README.md)
- [Application API and generation workflow](docs/api/README.md)
- [Operator user interface](docs/user-interface/README.md)
- [Contributing guide](CONTRIBUTING.md)
- [Architecture decisions](docs/adr/README.md)

## Preliminary technical direction

The scheduling engine will likely use a constraint solver such as Google OR-Tools CP-SAT. The API, user interface, and data storage stack will be selected after the requirements phase and a small solver prototype.
