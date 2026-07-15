# Weekly Lesson Counts from SRC-001

## Status and counting method

This reference records the weekly curriculum reconstructed from the supplied timetable.
Each numbered timetable position counts as one class period. Repeated foreign-language
labels in one position represent concurrent groups and count as one foreign-language
period for a pupil. Paired informatics and technology positions are counted once for each
subject across the week.

The repository owner confirmed that grades 5 through 9 do not use subject profiles, so
sections in the same grade must receive the same weekly counts. Profiles begin in grade
10. The timetable's slash order consistently exposes a mathematics-physics track and a
chemistry-biology track in sections 10A and 11A.

## Total periods by grade

| Grade or section | Daily pattern | Weekly total | Source result |
| --- | --- | ---: | --- |
| Grade 5 | Four 6-period days and one 5-period day | 29 | Sections 5A and 5B match; 5V (Cyrillic `В`) is missing three physical-education periods |
| Grade 6 | Five 6-period days | 30 | All sections match |
| Grade 7 | Four 6-period days and one 7-period day | 31 | All sections match |
| Grade 8 | Three 7-period days and two 6-period days | 33 | All sections match |
| Grade 9 | Three 7-period days and two 6-period days | 33 | All sections match after correcting one missing separator in 9A |
| Grade 10 | One or two 7-period days, remaining days 6 periods | 32 | Both sections match |
| Grade 11 | One or two 7-period days, remaining days 6 periods | 32 | Both sections match |

The incomplete 5V (Cyrillic `В`) column is treated as a source defect, not as a different curriculum.
Its missing three periods are physical education, which restores the confirmed grade-5
total of 29.

## Grades 5 through 9

All values are periods per pupil per week.

| Subject | Grade 5 | Grade 6 | Grade 7 | Grade 8 | Grade 9 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Mathematics | 5 | 5 | 5 | 5 | 5 |
| Russian language | 3 | 3 | 2 | 2 | 2 |
| Russian literature | 2 | 2 | 1 | 2 | 1 |
| Belarusian language | 3 | 3 | 2 | 2 | 2 |
| Belarusian literature | 2 | 2 | 2 | 1 | 2 |
| Foreign language | 5 | 5 | 5 | 5 | 5 |
| Physical education | 3 | 3 | 3 | 3 | 3 |
| Technology | 1 | 1 | 1 | 1 | 1 |
| Informatics | 0 | 1 | 1 | 1 | 1 |
| Art | 1 | 1 | 1 | 1 | 0 |
| Human and the World | 1 | 0 | 0 | 0 | 0 |
| Life safety | 1 | 0 | 0 | 0 | 0 |
| Biology | 0 | 1 | 2 | 2 | 2 |
| Geography | 0 | 1 | 1 | 2 | 1 |
| History of Belarus | 0 | 1 | 1 | 1 | 1 |
| World history | 2 | 1 | 1 | 1 | 2 |
| Physics | 0 | 0 | 2 | 2 | 2 |
| Chemistry | 0 | 0 | 1 | 2 | 2 |
| Social studies | 0 | 0 | 0 | 0 | 1 |
| **Total** | **29** | **30** | **31** | **33** | **33** |

## Grades 10 and 11

Sections 10A and 11A contain two concurrent profile tracks. Sections 10B and 11B contain
the general curriculum shown in the source.

| Subject | 10A mathematics-physics | 10A chemistry-biology | 10B general | 11A mathematics-physics | 11A chemistry-biology | 11B general |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Mathematics | 6 | 4 | 6 | 6 | 4 | 6 |
| Physics | 4 | 2 | 2 | 4 | 2 | 2 |
| Chemistry | 2 | 4 | 2 | 2 | 4 | 2 |
| Biology | 2 | 4 | 2 | 2 | 4 | 2 |
| Russian language | 1 | 1 | 1 | 2 | 2 | 2 |
| Russian literature | 2 | 2 | 2 | 1 | 1 | 1 |
| Belarusian language | 2 | 2 | 2 | 1 | 1 | 1 |
| Belarusian literature | 1 | 1 | 1 | 2 | 2 | 2 |
| Foreign language | 2 | 2 | 4 | 2 | 2 | 4 |
| Physical education | 3 | 3 | 3 | 3 | 3 | 3 |
| Informatics | 1 | 1 | 1 | 1 | 1 | 1 |
| Geography | 1 | 1 | 1 | 1 | 1 | 1 |
| History of Belarus | 2 | 2 | 2 | 2 | 2 | 2 |
| World history | 0 | 0 | 0 | 0 | 0 | 0 |
| Social studies | 1 | 1 | 1 | 1 | 1 | 1 |
| Technical drawing | 1 | 1 | 1 | 0 | 0 | 0 |
| Astronomy | 0 | 0 | 0 | 1 | 1 | 1 |
| Defense or medical training | 1 | 1 | 1 | 1 | 1 | 1 |
| **Total** | **32** | **32** | **32** | **32** | **32** | **32** |

## Implementation rules

- Grade-level curriculum templates must be reused by every section in grades 5 through 9.
- A grade-5 class must receive exactly 29 weekly periods and no more than six per day.
- Grade 6 must receive exactly 30 weekly periods and no more than six per day.
- Grades 7 through 11 may use a seventh period when required by their weekly total.
- Profile-specific requirements must target explicit groups rather than the entire class.
- Import validation must reject or flag section totals that differ from the grade template.
- The source document remains evidence for lesson counts, not for teachers or classrooms.
