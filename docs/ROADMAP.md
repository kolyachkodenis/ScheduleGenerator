# ScheduleGenerator Roadmap

The roadmap is divided into small, verifiable stages. Each stage must end with a working result or an explicit decision, not merely with code changes.

## Stage 0: Project organization

**Status:** Complete

- Define the product purpose and the boundaries of the first release.
- Identify the owner of school-side requirements.
- Choose how documentation and architectural decisions will be maintained.
- Set up issues, branches, code checks, and contribution templates.
- Establish a shared glossary for terms such as class, group, cohort, slot, shift, gap, and subject difficulty.

**Deliverable:** clear project conventions and consistent terminology.

## Stage 1: Study the real scheduling process

**Status:** In progress

- Document how timetables are currently created.
- Collect examples of curricula and completed timetables.
- Determine the structure of the school week, shifts, and lesson periods.
- Document class splitting, student groups, and combined lessons.
- Collect common exceptions and irregular-week scenarios.
- Identify who enters data, starts generation, reviews results, and publishes timetables.
- Agree on measurable criteria for a good timetable.

**Deliverable:** validated use cases and representative source data.

## Stage 2: Build the constraint catalog

**Status:** In progress

- Divide all rules into hard constraints and soft preferences.
- Prevent simultaneous lessons for the same class, teacher, or classroom.
- Account for teacher and classroom availability.
- Enforce the required weekly lesson count for every subject and class.
- Account for shifts, allowed slots, and daily lesson limits.
- Handle specialized classrooms and room capacity.
- Support split groups and lessons combining multiple classes.
- Define subject difficulty and a maximum difficult-subject load per day.
- Describe teacher gaps, balanced workloads, and undesirable first or last periods.
- Assign priorities and weights to soft preferences.
- Decide which preferences may be relaxed when no ideal solution exists.

**Deliverable:** a versioned rule catalog with examples and priorities.

## Stage 3: Design the data model

**Status:** In progress

- Model the school, academic year, terms, and week structure.
- Model classes and groups without storing unnecessary personal data.
- Model subjects, teachers, classrooms, and time slots.
- Model curriculum requirements and weekly lesson counts.
- Model availability, preferences, exceptions, and constraint weights.
- Model timetable versions and change history.
- Define validation rules and actionable error messages.
- Prepare a small reference dataset.

**Deliverable:** a documented schema and a valid demonstration dataset.

## Stage 4: Prototype the solver

**Status:** Complete

- Compare CP-SAT, MILP, and heuristic approaches on a small scheduling problem.
- Build a minimal solver without a user interface or database.
- Verify hard constraints using focused test cases.
- Add an objective function for soft preferences.
- Measure solve time for several school sizes.
- Test behavior with impossible input data.
- Produce useful diagnostics for unsatisfiable problems or conflicting rules.
- Record the solver choice in an architectural decision record.

**Deliverable:** a reproducible prototype and an evidence-based technology choice.

## Stage 5: Implement the scheduling core

**Status:** Complete

- Keep the school domain model independent of the selected solver.
- Validate input before starting a generation job.
- Convert validated domain data into the solver model.
- Calculate penalties for soft-constraint violations.
- Support solve-time limits and return the best solution found so far.
- Make runs reproducible through seeds and explicit parameters.
- Implement an independent validator for generated timetables.
- Produce a quality report with violated preferences and their costs.

**Deliverable:** a testable scheduling library.

## Stage 6: Test the scheduling core

**Status:** Complete for scheduling core 0.2.0

- Add unit tests for every hard constraint.
- Add unit tests for every soft constraint and penalty.
- Test impossible and contradictory problems.
- Add property-based tests for conflicts and required lesson counts.
- Maintain a collection of reference timetable scenarios.
- Add performance tests for small, medium, and large schools.
- Define acceptable generation time and memory use.

**Deliverable:** a reliable automated test suite protecting scheduling rules.

## Stage 7: Add data storage and import

**Status:** Complete for local school configuration 0.3.0

- Select a database and create migrations.
- Implement CRUD operations for all school reference data.
- Import XLSX and CSV files using documented templates.
- Add import previews before any data is saved.
- Report row-level and field-level errors without partially corrupting data.
- Support source-data export and backups.
- Provide demonstration data for local development.

**Deliverable:** a complete school configuration can be created without changing code.

## Stage 8: Build the API and generation workflow

**Status:** Complete for the transport-neutral application API 0.4.0

- Design APIs for reference data, rules, and preferences.
- Create and manage timetable generation jobs.
- Support progress reporting, cancellation, and time limits.
- Store the parameters, seed, result, and diagnostics for each run.
- Return multiple high-quality alternatives when requested.
- Validate timetables after manual changes.
- Document the API and add integration tests.

**Deliverable:** a stable programmatic interface for all core operations.

## Stage 9: Build the first user interface

- Create a school setup wizard.
- Add editors for classes, teachers, subjects, and classrooms.
- Add editors for availability and curriculum requirements.
- Add controls for subject difficulty and rule priorities.
- Start generation jobs and display their progress.
- Display timetables by class, teacher, and classroom.
- Show timetable quality and explain detected problems.

**Deliverable:** an operator can generate a timetable through the UI from start to finish.

## Stage 10: Support manual editing

- Move lessons with drag and drop or a dedicated dialog.
- Highlight hard conflicts immediately.
- Show how each change affects the quality score.
- Lock selected lessons before regenerating the rest of the timetable.
- Add undo, redo, and change history.
- Compare two timetable versions.

**Deliverable:** the generator assists the scheduler without removing human control.

## Stage 11: Export and publication

- Export timetables to XLSX and PDF.
- Produce printer-friendly layouts.
- Provide separate views for classes and teachers.
- Publish and unpublish approved versions.
- Add calendar export if required.
- Prevent draft timetables from being published accidentally.

**Deliverable:** approved timetables can be distributed safely.

## Stage 12: Users and security

- Define administrator, scheduler, reviewer, and reader roles.
- Implement authentication and authorization.
- Audit important actions.
- Minimize the collection and storage of personal data.
- Secure secrets and implement backup and recovery procedures.
- Perform a baseline security review.

**Deliverable:** the system can safely handle real school data.

## Stage 13: Operations and observability

- Provide containers and a reproducible local setup.
- Configure separate development, test, and production environments.
- Add structured logs and scheduling metrics.
- Add health checks and error monitoring.
- Configure CI for tests, linting, and builds.
- Document deployment, upgrade, rollback, and recovery procedures.

**Deliverable:** the application can be deployed and diagnosed reliably.

## Stage 14: Run a school pilot

- Load anonymized or appropriately authorized real data.
- Build the same timetable with the existing process and the new system.
- Compare time spent and result quality.
- Collect feedback from schedulers, teachers, and administrators.
- Tune preference weights using real feedback.
- Resolve critical issues and repeat the pilot.

**Deliverable:** evidence that the product improves a real scheduling process.

## Stage 15: Release version 1.0

- Document supported scenarios and known limitations.
- Complete user and administrator documentation.
- Prepare training material and a demonstration workflow.
- Run acceptance testing.
- Publish version 1.0 and define the maintenance process.

**Deliverable:** a product ready for regular use.

## Proposed MVP scope

The first working version should support:

- one school and one academic term;
- classes without complex individual learning paths;
- teachers, subjects, classrooms, and split groups;
- availability and hard conflict constraints;
- weekly curriculum requirements;
- subject difficulty and balanced daily workload;
- generation of one or more timetable alternatives;
- independent validation of generated results;
- locking lessons before partial regeneration;
- timetable views by class and teacher;
- XLSX import and export.

Integrations, mobile applications, teacher substitutions, and complex alternating-week patterns should be considered after the MVP succeeds.

## Preliminary technical risks

- Contradictory rules may make a scheduling problem unsatisfiable.
- A large number of soft constraints may increase solve time significantly.
- The subjective definition of a good timetable will require iterative weight tuning.
- Real source data will often be incomplete or internally inconsistent.
- Manual edits can invalidate constraints that were previously satisfied.
- Users will need understandable quality reports before they trust generated results.

## Next milestone

Complete discovery with representative real school data while starting Stage 9: build the first operator user interface on the stable application API.
