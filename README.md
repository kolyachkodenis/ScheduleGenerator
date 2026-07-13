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

The project is currently in the planning stage. Implementation has not started yet.

See the detailed [project roadmap](docs/ROADMAP.md).

## Preliminary technical direction

The scheduling engine will likely use a constraint solver such as Google OR-Tools CP-SAT. The API, user interface, and data storage stack will be selected after the requirements phase and a small solver prototype.

