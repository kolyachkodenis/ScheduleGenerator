# Manual timetable editing

Manual editing builds a versioned draft from a successful generation job. The generated result remains immutable as version 0.

## Editing workflow

1. Open a successful result and choose **Edit timetable**.
2. Drag a lesson to another cell or use its edit button to select a day, starting period, teacher, and classroom.
3. Review the hard-conflict banner and the recalculated quality penalty immediately after the move.
4. Lock lessons that must remain in place.
5. Choose **Regenerate unlocked** to pass the locked placements back to the solver as fixed lessons.
6. Use undo and redo to move through the linear version history.
7. Compare any two retained versions to see changed lessons, quality delta, and conflict delta.

An invalid move is retained as a draft version so the operator can understand and undo it, but the UI clearly reports every hard validation error. A locked lesson cannot be moved until it is unlocked.

## Persistence model

Each draft is pinned to the dataset revision used by its generation job. Assignment snapshots, quality reports, validation errors, and change descriptions are stored for every version. Locks belong to the draft and remain active while navigating history.

Creating a new edit after undo removes the abandoned redo branch. This keeps the first interface's history understandable while preserving all versions on the active branch.
