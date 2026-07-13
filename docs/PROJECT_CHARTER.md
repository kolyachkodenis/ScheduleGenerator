# Project Charter

## Purpose

ScheduleGenerator helps a school scheduler create a valid weekly timetable with less manual work. It treats timetable creation as a constraint-optimization problem while keeping the final decision under human control.

## Target users

- **Primary user:** the staff member responsible for building and maintaining the timetable.
- **Reviewers:** school administrators and department representatives who verify the result.
- **Readers:** teachers and students who consume an approved timetable.

## Product principles

1. A generated timetable must never hide hard-constraint violations.
2. Quality preferences must be measurable and explainable.
3. Manual editing remains available, with immediate revalidation.
4. Input errors should be reported before an expensive solver run.
5. Personal data collection must be minimized.
6. The same input, configuration, and random seed must reproduce a run.

## MVP boundaries

The MVP covers one school and one academic term. It includes classes, split groups, teachers, subjects, classrooms, time slots, curriculum requirements, availability, subject difficulty, generation, validation, lesson locking, views by class and teacher, and XLSX import and export.

The MVP does not include:

- individual student timetables;
- teacher substitution management;
- mobile applications;
- external school-information-system integrations;
- complex alternating-week patterns;
- automatic publication to third-party services.

These boundaries may change only through a documented decision.

## Success criteria

Before version 1.0, the project must demonstrate that it can:

- produce a timetable with no hard conflicts for an agreed reference dataset;
- satisfy all required weekly lesson counts;
- explain violated soft preferences and their impact on the score;
- validate manual changes immediately;
- finish a representative generation job within an agreed time budget;
- reduce the scheduler's active work compared with the current process.

Numerical targets will be set during discovery after representative school data is available.

## Ownership and decisions

- **Repository owner and technical decision owner:** [@kolyachkodenis](https://github.com/kolyachkodenis).
- **School-side requirements owner:** not assigned yet. A domain representative must be named before Stage 1 can be approved.
- Product-scope decisions are recorded in the roadmap or project charter.
- Technical decisions with long-term consequences are recorded as architecture decision records.
- A stage is complete only when its stated deliverable can be reviewed.

## Current milestone

Stage 1 is in progress. The discovery package is ready, but the process, use cases, quality targets, and representative examples still require validation by a school-side requirements owner.

