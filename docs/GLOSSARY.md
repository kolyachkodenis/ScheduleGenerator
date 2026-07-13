# Domain Glossary

This glossary defines the terms used in requirements, code, tests, and user-facing documentation.

| Term | Definition |
| --- | --- |
| Academic term | A period for which curriculum requirements and a timetable are valid, such as a semester or quarter. |
| Availability | The set of time slots in which a resource is allowed to participate in a lesson. |
| Class | A stable group of students following a shared curriculum, such as Grade 7A. |
| Classroom | A physical room in which a lesson can take place. It may have capacity or equipment requirements. |
| Cohort | One or more classes or groups taught together in the same lesson. |
| Constraint | A rule evaluated while generating or validating a timetable. |
| Constraint instance | One application of a constraint definition to specific resources, requirements, or time slots. |
| Curriculum requirement | The required number and type of lessons for a subject, class, or group during an academic period. |
| Difficult subject | A subject assigned a workload score used to limit or balance cognitive load. |
| Gap | An unused time slot between two assigned lessons for the same class or teacher. |
| Generation run | One solver execution with a fixed input version, configuration, time limit, and random seed. |
| Group | A subset of a class created for lessons taught separately, such as language or laboratory groups. |
| Hard constraint | A rule that every accepted timetable must satisfy. A violation makes the timetable invalid. |
| Feasible timetable | A timetable that satisfies every enabled hard constraint. |
| Lesson | A scheduled teaching event involving a subject, one or more classes or groups, one or more teachers, and usually a classroom. |
| Lesson period | An ordinal position in a school day, such as the third lesson. |
| Locked lesson | A lesson fixed to its current assignment and preserved during regeneration. |
| Preference weight | A numerical value expressing the relative importance of a soft constraint. |
| Penalty | A non-negative cost produced by violating or partially satisfying a soft constraint. |
| Resource | An entity whose simultaneous use must be controlled, such as a teacher, class, group, or classroom. |
| Shift | A recurring part of the day in which a set of classes is taught, such as a morning shift. |
| Soft constraint | A preference that may be violated at a measurable penalty when necessary. |
| Validation status | The evidence state of a rule: draft, reported, confirmed, rejected, or superseded. |
| Subject | An area of instruction, such as Mathematics or History. |
| Time slot | A specific combination of school day and lesson period available for assignment. |
| Timetable | A versioned set of lesson assignments for a defined academic period and week pattern. |
| Unsatisfiable problem | Input and hard constraints for which no valid timetable exists. |
| Workload score | A value used to estimate and balance lesson difficulty for a class or teacher. |

When a new domain term is introduced, add it here before relying on it in implementation-specific documentation.
