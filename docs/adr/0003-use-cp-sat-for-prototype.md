# ADR 0003: Use OR-Tools CP-SAT for the scheduling prototype

- **Status:** Accepted for prototype
- **Date:** 2026-07-13
- **Owner:** [@kolyachkodenis](https://github.com/kolyachkodenis)

## Context

School timetabling combines assignment, non-overlap, availability, consecutive-block, cardinality, and weighted-preference rules. The prototype must find feasible schedules, optimize integer penalties, stop at a time limit, and report whether a result is optimal, merely feasible, infeasible, or unknown.

## Decision

Use Google OR-Tools CP-SAT 9.15.6755 for the Stage 4 prototype. Model each lesson occurrence as one selection among precomputed feasible combinations of start slot, eligible teacher, and suitable classroom. Enforce resource conflicts and daily limits as hard constraints and minimize supported soft-constraint penalties.

Keep domain parsing, validation, and solution verification outside the solver model so the scheduling core is not permanently coupled to CP-SAT data structures.

This decision selects the prototype technology. Production adoption will be reconfirmed after representative school data and performance measurements are available.

## Alternatives considered

### Mixed-integer linear programming

MILP has mature optimization theory, strong commercial solvers, and clear linear formulations. It remains a credible alternative. However, timetable logic frequently requires reified conditions, optional assignments, consecutive blocks, and logical combinations that CP-SAT expresses more directly with Boolean and integer constraints. High-quality commercial MILP performance may also introduce licensing and deployment choices too early.

### Custom constructive heuristic

A domain-specific heuristic can produce an initial result quickly and may become useful as a warm start. On its own, it is difficult to prove infeasibility or optimality, easy to make nondeterministic, and requires custom repair logic for every new constraint interaction.

### General backtracking constraint solver

Backtracking is useful for education and very small cases but would duplicate propagation, search, and optimization capabilities already available in maintained solvers.

## Consequences

- All CP-SAT coefficients and variables use integers.
- The prototype pins a large binary dependency and must test supported Python platforms.
- Candidate precomputation can reduce model size but must provide diagnostics when it removes every candidate for an occurrence.
- Weighted objectives require bounded, tested coefficients; future work should implement approved lexicographic tiers.
- An independent validator must check every returned solution rather than trusting solver construction alone.
- Real datasets may reveal a need to revisit MILP, hybrid search, or solver warm starts.

