# Preference Priority Model

## Goals

The scoring model must be understandable, configurable, and resistant to accidental trade-offs. A large number of minor improvements must not silently compensate for violating a preference that the school considers substantially more important.

## Proposed priority tiers

| Tier | Meaning | Candidate examples |
| --- | --- | --- |
| P0 | Hard feasibility; never part of the optimization score. | Resource non-overlap, required lesson coverage, mandatory availability. |
| P1 | Critical operational preference; violating it requires prominent explanation. | Excess difficult-subject load, prohibited-in-practice class gaps. |
| P2 | Important quality preference. | Balanced class load, subject spread, teacher gaps. |
| P3 | Convenience or presentation preference. | Preferred time windows, optional room suitability. |

Tier assignment remains draft until school-side approval.

## Proposed optimization approach

Use lexicographic optimization when the solver supports it reliably:

1. find a timetable satisfying all P0 hard constraints;
2. minimize the total normalized P1 penalty;
3. without worsening the best accepted P1 value, minimize P2;
4. without worsening higher tiers, minimize P3.

If the chosen solver implementation uses one weighted objective, calculate weight ranges so that the maximum possible penalty of every lower tier cannot outweigh one unit of the next higher tier. The calculation and bounds must be covered by tests.

## Penalty requirements

Every soft constraint must define:

- a zero-penalty condition;
- a non-negative unit of violation;
- whether penalty growth is linear, stepped, or nonlinear;
- its maximum possible penalty for one instance and one dataset;
- normalization, if schools configure different scales;
- the resources and assignments included in its diagnostic output.

Weights must not be used to convert an actual hard rule into a hidden preference.

## Configuration hierarchy

A future configuration model may apply defaults and overrides in this order:

1. product-safe default;
2. school-wide policy;
3. grade or shift policy;
4. subject, class, teacher, or classroom override;
5. generation-run experiment.

More specific configuration may override only fields explicitly declared overridable. Every effective value must be explainable with its source.

## Calibration process

1. Ask stakeholders to rank concrete timetable pairs instead of assigning arbitrary numbers.
2. Map the comparisons to priority tiers.
3. Choose initial within-tier weights.
4. run sanitized historical scenarios;
5. compare solver ranking with scheduler ranking;
6. adjust one documented parameter set at a time;
7. approve and version the resulting policy.

The raw solver score is not meaningful across datasets unless penalty bounds and normalization are held constant.

