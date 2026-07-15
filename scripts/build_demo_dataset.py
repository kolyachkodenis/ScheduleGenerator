"""Build the representative demonstration school dataset."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "examples" / "small-school.json"

DAYS = [
    ("mon", "Monday"),
    ("tue", "Tuesday"),
    ("wed", "Wednesday"),
    ("thu", "Thursday"),
    ("fri", "Friday"),
]
PERIODS = [
    ("p1", "Period 1", "08:00", "08:45"),
    ("p2", "Period 2", "08:55", "09:40"),
    ("p3", "Period 3", "10:00", "10:45"),
    ("p4", "Period 4", "11:05", "11:50"),
    ("p5", "Period 5", "12:00", "12:45"),
    ("p6", "Period 6", "12:55", "13:40"),
    ("p7", "Period 7", "13:50", "14:35"),
]
SECTIONS = {
    5: ("a", "b", "v"),
    6: ("a", "b", "v"),
    7: ("a", "b", "v"),
    8: ("a", "b"),
    9: ("a", "b", "v"),
    10: ("a", "b"),
    11: ("a", "b"),
}
SECTION_LABELS = {"a": "A", "b": "B", "v": "V"}

SUBJECTS = [
    ("mathematics", "Mathematics", 3),
    ("russian_language", "Russian Language", 3),
    ("russian_literature", "Russian Literature", 2),
    ("belarusian_language", "Belarusian Language", 3),
    ("belarusian_literature", "Belarusian Literature", 2),
    ("english", "English", 2),
    ("physical_education", "Physical Education", 1),
    ("technology", "Technology", 1),
    ("informatics", "Informatics", 2),
    ("art", "Art", 1),
    ("human_and_world", "Human and the World", 1),
    ("life_safety", "Life Safety", 1),
    ("biology", "Biology", 3),
    ("geography", "Geography", 2),
    ("history_belarus", "History of Belarus", 2),
    ("world_history", "World History", 2),
    ("physics", "Physics", 3),
    ("chemistry", "Chemistry", 3),
    ("social_studies", "Social Studies", 2),
    ("technical_drawing", "Technical Drawing", 2),
    ("astronomy", "Astronomy", 3),
    ("defense_medical", "Defense and Medical Training", 1),
]

COMMON_COUNTS = {
    5: {
        "mathematics": 5, "russian_language": 3, "russian_literature": 2,
        "belarusian_language": 3, "belarusian_literature": 2, "english": 5,
        "physical_education": 3, "technology": 1, "art": 1,
        "human_and_world": 1, "life_safety": 1, "world_history": 2,
    },
    6: {
        "mathematics": 5, "russian_language": 3, "russian_literature": 2,
        "belarusian_language": 3, "belarusian_literature": 2, "english": 5,
        "physical_education": 3, "technology": 1, "informatics": 1, "art": 1,
        "biology": 1, "geography": 1, "history_belarus": 1, "world_history": 1,
    },
    7: {
        "mathematics": 5, "russian_language": 2, "russian_literature": 1,
        "belarusian_language": 2, "belarusian_literature": 2, "english": 5,
        "physical_education": 3, "technology": 1, "informatics": 1, "art": 1,
        "biology": 2, "geography": 1, "history_belarus": 1, "world_history": 1,
        "physics": 2, "chemistry": 1,
    },
    8: {
        "mathematics": 5, "russian_language": 2, "russian_literature": 2,
        "belarusian_language": 2, "belarusian_literature": 1, "english": 5,
        "physical_education": 3, "technology": 1, "informatics": 1, "art": 1,
        "biology": 2, "geography": 2, "history_belarus": 1, "world_history": 1,
        "physics": 2, "chemistry": 2,
    },
    9: {
        "mathematics": 5, "russian_language": 2, "russian_literature": 1,
        "belarusian_language": 2, "belarusian_literature": 2, "english": 5,
        "physical_education": 3, "technology": 1, "informatics": 1,
        "biology": 2, "geography": 1, "history_belarus": 1, "world_history": 2,
        "physics": 2, "chemistry": 2, "social_studies": 1,
    },
}

UPPER_COUNTS = {
    "10a": {
        "mathematics": 6, "physics": 4, "chemistry": 2, "biology": 2,
        "russian_language": 1, "russian_literature": 2, "belarusian_language": 2,
        "belarusian_literature": 1, "english": 2, "physical_education": 3,
        "informatics": 1, "geography": 1, "history_belarus": 2,
        "social_studies": 1, "technical_drawing": 1, "defense_medical": 1,
    },
    "10b": {
        "mathematics": 6, "physics": 2, "chemistry": 2, "biology": 2,
        "russian_language": 1, "russian_literature": 2, "belarusian_language": 2,
        "belarusian_literature": 1, "english": 4, "physical_education": 3,
        "informatics": 1, "geography": 1, "history_belarus": 2,
        "social_studies": 1, "technical_drawing": 1, "defense_medical": 1,
    },
    "11a": {
        "mathematics": 4, "physics": 2, "chemistry": 4, "biology": 4,
        "russian_language": 2, "russian_literature": 1, "belarusian_language": 1,
        "belarusian_literature": 2, "english": 2, "physical_education": 3,
        "informatics": 1, "geography": 1, "history_belarus": 2,
        "social_studies": 1, "astronomy": 1, "defense_medical": 1,
    },
    "11b": {
        "mathematics": 6, "physics": 2, "chemistry": 2, "biology": 2,
        "russian_language": 2, "russian_literature": 1, "belarusian_language": 1,
        "belarusian_literature": 2, "english": 4, "physical_education": 3,
        "informatics": 1, "geography": 1, "history_belarus": 2,
        "social_studies": 1, "astronomy": 1, "defense_medical": 1,
    },
}

TEACHER_DEFINITIONS = [
    ("t_math", "Smirnov", ["mathematics"]),
    ("t_math_2", "Kuznetsova", ["mathematics"]),
    ("t_math_3", "Sokolov", ["mathematics"]),
    ("t_math_4", "Volkova", ["mathematics"]),
    ("t_math_5", "Popov", ["mathematics"]),
    ("t_math_6", "Medvedeva", ["mathematics"]),
    ("t_math_7", "Denisov", ["mathematics"]),
    ("t_russian_1", "Ivanov", ["russian_language", "russian_literature"]),
    ("t_russian_2", "Morozova", ["russian_language", "russian_literature"]),
    ("t_russian_3", "Lebedev", ["russian_language", "russian_literature"]),
    ("t_belarusian_1", "Kovalenko", ["belarusian_language", "belarusian_literature"]),
    ("t_belarusian_2", "Shevchenko", ["belarusian_language", "belarusian_literature"]),
    ("t_belarusian_3", "Bondarenko", ["belarusian_language", "belarusian_literature"]),
    ("t_english_1", "Taylor", ["english"]),
    ("t_english_2", "Brown", ["english"]),
    ("t_english_3", "Wilson", ["english"]),
    ("t_english_4", "Cooper", ["english"]),
    ("t_english_5", "Harris", ["english"]),
    ("t_english_6", "Martin", ["english"]),
    ("t_pe_1", "Orlov", ["physical_education"]),
    ("t_pe_2", "Pavlova", ["physical_education"]),
    ("t_pe_3", "Zaitsev", ["physical_education"]),
    ("t_pe_4", "Karpov", ["physical_education"]),
    ("t_pe_5", "Kulikov", ["physical_education"]),
    ("t_physics", "Fedorov", ["physics", "astronomy"]),
    ("t_physics_2", "Vinogradov", ["physics", "astronomy"]),
    ("t_chemistry", "Mikhailova", ["chemistry"]),
    ("t_chemistry_2", "Belyaeva", ["chemistry"]),
    ("t_biology", "Egorova", ["biology"]),
    ("t_biology_2", "Nikolaeva", ["biology"]),
    ("t_biology_3", "Alexeev", ["biology"]),
    ("t_belarus_history", "Novik", ["history_belarus"]),
    ("t_belarus_history_2", "Kravchenko", ["history_belarus"]),
    ("t_belarus_history_3", "Savchenko", ["history_belarus"]),
    ("t_world_history", "Romanov", ["world_history"]),
    ("t_world_history_2", "Semenov", ["world_history"]),
    ("t_world_history_3", "Gromov", ["world_history"]),
    ("t_geography", "Kozlova", ["geography", "social_studies"]),
    ("t_geography_2", "Sorokina", ["geography", "social_studies"]),
    ("t_geography_3", "Vasiliev", ["geography", "social_studies"]),
    ("t_technology", "Andreev", ["technology", "technical_drawing"]),
    ("t_technology_2", "Tarasov", ["technology", "technical_drawing"]),
    ("t_technology_3", "Bogdanov", ["technology", "technical_drawing"]),
    ("t_art", "Petrov", ["art", "human_and_world", "life_safety"]),
    ("t_art_2", "Golubeva", ["art", "human_and_world", "life_safety"]),
    ("t_art_3", "Komarov", ["art", "human_and_world", "life_safety"]),
    ("t_art_4", "Fomina", ["art", "human_and_world", "life_safety"]),
    ("t_informatics", "Markov", ["informatics"]),
    ("t_informatics_2", "Zhukov", ["informatics"]),
    ("t_informatics_3", "Kiselev", ["informatics"]),
    ("t_defense", "Belov", ["defense_medical"]),
]

SUBJECT_TEACHER_POOLS = {
    "mathematics": ("t_math", "t_math_2", "t_math_3", "t_math_4", "t_math_5", "t_math_6", "t_math_7"),
    "russian_language": ("t_russian_1", "t_russian_2", "t_russian_3"),
    "russian_literature": ("t_russian_1", "t_russian_2", "t_russian_3"),
    "belarusian_language": ("t_belarusian_1", "t_belarusian_2", "t_belarusian_3"),
    "belarusian_literature": ("t_belarusian_1", "t_belarusian_2", "t_belarusian_3"),
    "english": ("t_english_1", "t_english_2", "t_english_3", "t_english_4", "t_english_5", "t_english_6"),
    "physical_education": ("t_pe_1", "t_pe_2", "t_pe_3", "t_pe_4", "t_pe_5"),
    "physics": ("t_physics", "t_physics_2"),
    "astronomy": ("t_physics", "t_physics_2"),
    "chemistry": ("t_chemistry", "t_chemistry_2"),
    "biology": ("t_biology", "t_biology_2", "t_biology_3"),
    "history_belarus": ("t_belarus_history", "t_belarus_history_2", "t_belarus_history_3"),
    "world_history": ("t_world_history", "t_world_history_2", "t_world_history_3"),
    "geography": ("t_geography", "t_geography_2", "t_geography_3"),
    "social_studies": ("t_geography", "t_geography_2", "t_geography_3"),
    "technology": ("t_technology", "t_technology_2", "t_technology_3"),
    "technical_drawing": ("t_technology", "t_technology_2", "t_technology_3"),
    "art": ("t_art", "t_art_2", "t_art_3", "t_art_4"),
    "human_and_world": ("t_art", "t_art_2", "t_art_3", "t_art_4"),
    "life_safety": ("t_art", "t_art_2", "t_art_3", "t_art_4"),
    "informatics": ("t_informatics", "t_informatics_2", "t_informatics_3"),
    "defense_medical": ("t_defense",),
}


def class_key(grade: int, section: str) -> str:
    return f"{grade}{section}"


def class_label(grade: int, section: str) -> str:
    return f"Class {grade}{SECTION_LABELS[section]}"


def counts_for(grade: int, section: str) -> dict[str, int]:
    return dict(COMMON_COUNTS[grade] if grade <= 9 else UPPER_COUNTS[class_key(grade, section)])


def daily_pattern(grade: int) -> tuple[int, ...]:
    if grade == 5:
        return (6, 6, 6, 6, 5)
    if grade == 6:
        return (6, 6, 6, 6, 6)
    if grade == 7:
        return (6, 6, 7, 6, 6)
    if grade <= 9:
        return (7, 7, 7, 6, 6)
    return (7, 7, 6, 6, 6)


def build() -> dict:
    classes = []
    teachers = [
        {"id": teacher_id, "label": label, "qualified_subject_ids": subjects}
        for teacher_id, label, subjects in TEACHER_DEFINITIONS
    ]
    classrooms = []
    requirements = []
    daily_limits = []
    difficult_targets = []
    resource_availability = []
    for grade, sections in SECTIONS.items():
        for section in sections:
            key = class_key(grade, section)
            class_id = f"class_{key}"
            room_id = f"room_{key}"
            student_count = 24 + ((grade + ord(section[0])) % 5)
            classes.append({
                "id": class_id,
                "label": class_label(grade, section),
                "grade": grade,
                "student_count": student_count,
                "shift_id": "morning",
            })
            classrooms.append({
                "id": room_id,
                "label": f"Room {grade}{SECTION_LABELS[section]}",
                "capacity": 30,
                "capabilities": ["general", "sports", "physics_lab", "chemistry_lab", "computer_lab", "workshop", "art"],
            })
            daily_limits.append(
                {"resource": {"type": "class", "id": class_id}, "maximum": 6 if grade <= 6 else 7}
            )
            difficult_targets.append({
                "participant": {"type": "class", "id": class_id},
                "target": 11 if grade <= 6 else 13,
            })
            pattern = daily_pattern(grade)
            resource_availability.append({
                "resource": {"type": "class", "id": class_id},
                "unavailable_slots": [
                    {"day_id": DAYS[day_index][0], "period_id": period[0]}
                    for day_index, lesson_count in enumerate(pattern)
                    for period in PERIODS[lesson_count:]
                ],
                "preferred_slots": [],
            })
            for subject_id, weekly_lessons in counts_for(grade, section).items():
                requirement_id = f"req_{key}_{subject_id}"
                eligible_teacher_ids = list(SUBJECT_TEACHER_POOLS[subject_id])
                allowed_classroom_ids = [room_id]
                capabilities = ["general"]
                block_length = 1

                if key == "7a" and subject_id == "mathematics":
                    requirement_id = "req_7a_math"
                elif key == "7a" and subject_id == "physics":
                    requirement_id = "req_7a_physics"
                elif key == "7a" and subject_id == "english":
                    requirement_id = "req_7a_en_1"
                elif key == "7a" and subject_id == "art":
                    requirement_id = "req_joint_advisory"
                elif key == "8a" and subject_id == "chemistry":
                    requirement_id = "req_8a_chemistry"
                    block_length = 2
                elif key == "8a" and subject_id == "english":
                    requirement_id = "req_8a_english"

                requirements.append({
                    "id": requirement_id,
                    "participant": {"type": "class", "id": class_id},
                    "subject_id": subject_id,
                    "eligible_teacher_ids": eligible_teacher_ids,
                    "weekly_lessons": weekly_lessons,
                    "block_length": block_length,
                    "required_room_capabilities": capabilities,
                    "allowed_classroom_ids": allowed_classroom_ids,
                })
    daily_limits.extend(
        {"resource": {"type": "teacher", "id": teacher["id"]}, "maximum": 7}
        for teacher in teachers
    )
    resource_availability.append(
        {
            "resource": {"type": "teacher", "id": "t_defense"},
            "unavailable_slots": [],
            "preferred_slots": [],
        }
    )

    return {
        "schema_version": "0.1.0",
        "dataset_id": "small_school_demo",
        "school": {"id": "demo_school", "label": "Representative Demonstration School", "timezone": "Europe/Minsk"},
        "academic_period": {
            "id": "term_1_2026", "label": "Demonstration Term 1", "start_date": "2026-09-01", "end_date": "2026-12-24",
            "days": [{"id": item[0], "label": item[1], "ordinal": index} for index, item in enumerate(DAYS, 1)],
            "periods": [{"id": item[0], "label": item[1], "ordinal": index, "start_time": item[2], "end_time": item[3]} for index, item in enumerate(PERIODS, 1)],
            "shifts": [{"id": "morning", "label": "Morning shift", "period_ids": [item[0] for item in PERIODS]}],
        },
        "subjects": [{"id": item[0], "label": item[1], "default_workload": item[2]} for item in SUBJECTS],
        "teachers": teachers,
        "classrooms": classrooms,
        "classes": classes,
        "group_partitions": [{"id": "partition_7a_english", "label": "Class 7A English groups", "class_id": "class_7a", "complete": True}],
        "groups": [
            {"id": "group_7a_en_1", "label": "Class 7A English Group 1", "class_id": "class_7a", "partition_id": "partition_7a_english", "student_count": 14},
            {"id": "group_7a_en_2", "label": "Class 7A English Group 2", "class_id": "class_7a", "partition_id": "partition_7a_english", "student_count": 14},
        ],
        "cohorts": [{"id": "cohort_7a_8a_advisory", "label": "Classes 7A and 8A Advisory", "members": [{"type": "class", "id": "class_7a"}, {"type": "class", "id": "class_8a"}]}],
        "curriculum_requirements": requirements,
        "resource_availability": resource_availability,
        "fixed_lessons": [{"id": "fixed_joint_advisory", "requirement_id": "req_joint_advisory", "occurrence_index": 0, "slot": {"day_id": "mon", "period_id": "p1"}, "teacher_id": "t_art", "classroom_id": "room_7a"}],
        "policies": {
            "daily_limits": daily_limits,
            "difficult_load_targets": difficult_targets,
            "soft_constraint_weights": [
                {"constraint_id": "SC-001", "priority": "P1", "weight": 10},
                {"constraint_id": "SC-002", "priority": "P1", "weight": 40},
                {"constraint_id": "SC-003", "priority": "P1", "weight": 200},
                {"constraint_id": "SC-004", "priority": "P2", "weight": 10},
                {"constraint_id": "SC-005", "priority": "P2", "weight": 30},
                {"constraint_id": "SC-019", "priority": "P2", "weight": 30},
            ],
        },
        "timetable_versions": [],
    }


if __name__ == "__main__":
    OUTPUT.write_text(json.dumps(build(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT}")
