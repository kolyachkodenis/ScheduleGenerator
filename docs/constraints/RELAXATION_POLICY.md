# Constraint Relaxation Policy

## Principle

An accepted timetable must satisfy every enabled hard constraint. The system must not automatically weaken a hard rule merely to return a result.

## Normal generation

- Hard constraints define feasibility and cannot be violated.
- Soft constraints may be violated according to their approved priority and weight.
- The result reports penalty totals and concrete soft-constraint violations.
- Reaching a time limit may return the best feasible timetable found, clearly labeled as not proven optimal.

## Unsatisfiable input

When no feasible timetable is found, the system should:

1. distinguish proven infeasibility from a time limit with no solution found;
2. identify a small or actionable set of conflicting rules and inputs when supported;
3. refer to stable constraint IDs and affected resources;
4. suggest candidate configuration changes without applying them;
5. require an authorized user to choose and record any change;
6. run validation again after the change.

## Allowed relaxation

Only soft constraints are relaxable during normal generation. Their penalties express the cost of relaxation.

A rule currently modeled as hard may change only through a versioned requirements decision that:

- identifies the existing constraint ID;
- records the business justification and approving role;
- defines the replacement hard or soft behavior;
- creates a new constraint ID when semantics materially change;
- updates examples, diagnostics, configuration, and tests;
- preserves the old rule as rejected or superseded.

## Emergency overrides

The MVP should not include a generic bypass that produces an invalid timetable. If a future operational need requires overrides, each override must be narrowly typed, explicitly authorized, time-bounded, visible in every affected view, and included in validation and audit reports.

## Diagnostic contract

Every reported conflict or relaxation should include:

- constraint ID and configured rule name;
- affected lesson requirements and resources;
- relevant days and time slots;
- source of the effective configuration;
- whether the rule is hard or soft;
- current penalty for a soft rule;
- possible user actions, phrased as options rather than automatic decisions.

