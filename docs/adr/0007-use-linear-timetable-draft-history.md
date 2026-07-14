# ADR 0007: Use linear version history for timetable drafts

- Status: Accepted
- Date: 2026-07-14

## Context

Operators need to move lessons safely, inspect conflicts and quality changes, undo mistakes, lock accepted placements, and partially regenerate a timetable. Generated results must remain reproducible and immutable.

## Decision

Create a persistent draft from a successful generation result. Store complete assignment snapshots, quality, validation errors, and change metadata for every version. Use a movable current-version pointer for undo and redo. A new edit after undo replaces the abandoned redo branch.

Store locks separately from versions. Convert locked assignments into fixed lessons when regenerating, while preserving fixed lessons from the source dataset.

## Consequences

- Every active edit can be inspected, compared, undone, and reproduced.
- Invalid manual states remain visible without overwriting the generated result.
- Full snapshots simplify correctness and recovery at the expected MVP scale.
- Branching histories and collaborative merge behavior are deferred.
