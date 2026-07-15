# Scheduling-Process Discovery

This directory is the working package for Roadmap Stage 1. It separates confirmed requirements from hypotheses so that implementation does not accidentally encode unverified assumptions.

## Documents

- [Process model](PROCESS.md): proposed as-is workflow, participants, handoffs, and exception paths.
- [Use cases](USE_CASES.md): user goals and acceptance outcomes independent of implementation.
- [Interview guide](INTERVIEW_GUIDE.md): questions for the scheduler and school representatives.
- [Data request](DATA_REQUEST.md): sanitized examples needed to validate requirements.
- [Timetable sample analysis](TIMETABLE_SAMPLE_ANALYSIS.md): observations and limitations from the first supplied weekly timetable.
- [Quality criteria](QUALITY_CRITERIA.md): candidate metrics and the process for approving targets.
- [Open questions](OPEN_QUESTIONS.md): unresolved decisions that can change product behavior.

## Evidence levels

Every material discovery statement should use one of these evidence levels:

| Level | Meaning |
| --- | --- |
| Confirmed | Explicitly approved by the assigned school-side requirements owner. |
| Reported | Described by a participant but not yet cross-checked or approved. |
| Observed | Demonstrated in a real artifact or scheduling session. |
| Hypothesis | A plausible starting point that still requires validation. |
| Rejected | Considered and explicitly determined not to apply. |

Most workflow details in this package remain hypotheses. The first completed timetable is recorded as observed evidence in the [sample analysis](TIMETABLE_SAMPLE_ANALYSIS.md), but its group semantics, scheduling rules, and quality targets still require school-side clarification. The high-level need to account for classes, teachers, and excessive difficult-subject load comes from the repository owner.

## Stage 1 completion gate

Stage 1 may move to `Complete` only when all of the following are true:

- a school-side requirements owner is named;
- at least one scheduler interview is recorded in summarized, non-personal form;
- the actual scheduling workflow and roles are approved;
- the school week, shifts, and lesson periods are documented;
- class splitting and combined-lesson patterns are documented;
- common exceptions and irregular weeks are documented;
- the primary use cases are approved;
- candidate quality metrics have agreed targets or priorities;
- the required source artifacts have been received in sanitized form;
- all blocking questions in `OPEN_QUESTIONS.md` are resolved.

## How to run discovery

1. Assign the school-side requirements owner.
2. Send the data request before the interview so examples are available.
3. Conduct the scheduler interview using the guide.
4. Walk through one timetable from initial inputs to publication.
5. Update each document with evidence levels and source references.
6. Review the resulting package with the requirements owner.
7. Record approval and update the roadmap status.

Do not commit real names, contact details, student data, credentials, or unrestricted school documents to the repository.
