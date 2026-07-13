# Scheduler Interview Guide

## Purpose

Use this guide for a 60–90 minute interview with the person who currently builds the timetable. Ask for concrete examples and demonstrations instead of accepting only general descriptions.

## Before the interview

- Assign a note taker and a facilitator.
- Review the data-safety rules in `DATA_REQUEST.md`.
- Obtain permission before recording audio, video, or screens.
- Ask the participant to prepare one sanitized timetable and its source inputs.
- Do not collect student names or unrelated personnel information.

## Part 1: Context and ownership

1. What period and parts of the school does this timetable cover?
2. Who is responsible for creating it, and who approves it?
3. Who supplies each type of input?
4. When does scheduling begin, and what is the publication deadline?
5. Which inputs usually arrive late or change frequently?
6. What tools and file formats are used today?

## Part 2: Walk through a real timetable

1. Show the starting files or systems.
2. Explain the first scheduling decision and why it comes first.
3. Continue through the major steps until publication.
4. Identify every manual check performed along the way.
5. Show how conflicts and missing information are tracked.
6. Explain which parts require the most judgment or repeated work.
7. Estimate active work time and total elapsed time.

## Part 3: Calendar and lesson structure

1. Which days are normally taught?
2. How many shifts and lesson periods exist?
3. Do bell times differ by day, grade, building, or shift?
4. Are zero periods, lunch periods, assemblies, or shortened days used?
5. Are double or consecutive lessons required for some subjects?
6. Are alternating-week or term-specific patterns required?

## Part 4: Classes, groups, and combined teaching

1. How are classes identified?
2. For which subjects are classes split into groups?
3. Can group membership differ by subject?
4. Are groups from different classes taught together?
5. Can multiple teachers teach one lesson?
6. Can a teacher supervise several groups at once?
7. Which of these patterns must the MVP support?

## Part 5: Teachers and classrooms

1. How are subject-to-teacher assignments provided?
2. Can several teachers be eligible for one requirement?
3. Which availability constraints are non-negotiable?
4. How are part-time teachers and teachers working across schools handled?
5. Which lessons require specialized classrooms or equipment?
6. May a class remain in a home classroom while teachers move?
7. How are room capacity and building travel time handled?

## Part 6: Workload and quality

1. What makes a subject difficult, and who decides its difficulty?
2. How many difficult lessons are acceptable per class per day?
3. Does acceptable difficulty depend on grade or lesson position?
4. How should lessons be balanced across the week?
5. Are class gaps allowed? Are teacher gaps allowed?
6. Which first-period and last-period assignments are undesirable?
7. What makes one valid timetable better than another?
8. Which preferences may be sacrificed first?

## Part 7: Exceptions and infeasibility

1. Describe the most common reason a timetable cannot satisfy every request.
2. Who decides which requirement to relax?
3. How are fixed events, absences, and shortened days handled?
4. What happens when curriculum hours and available slots do not match?
5. What explanation would help resolve an impossible case?
6. Which exceptional cases may be handled manually outside the MVP?

## Part 8: Review, publication, and changes

1. Who reviews class, teacher, and classroom views?
2. Which checks must pass before approval?
3. What output formats and layouts are required?
4. Where is the approved source of truth published?
5. How are drafts distinguished from approved versions?
6. How are later corrections made, approved, and communicated?

## Part 9: Measures of success

1. How long does the current process take?
2. How many revision cycles are typical?
3. Which defects are most costly?
4. What generation wait time would be acceptable?
5. What improvement would make the first release worth adopting?

## After the interview

- Summarize statements without personal information.
- Label each statement as reported, observed, or still hypothetical.
- Update the process model, use cases, quality criteria, and open questions.
- Ask the participant to correct the summary.
- Obtain final approval from the requirements owner, not merely interview attendance.

