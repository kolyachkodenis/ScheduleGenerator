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
    teachers = []
    classrooms = []
    requirements = []
    daily_limits = []
    difficult_targets = []
    resource_availability = []
    all_subject_ids = [item[0] for item in SUBJECTS]

    for grade, sections in SECTIONS.items():
        for section in sections:
            key = class_key(grade, section)
            class_id = f"class_{key}"
            teacher_id = "t_math" if key == "5a" else f"t_{key}"
            room_id = f"room_{key}"
            student_count = 24 + ((grade + ord(section[0])) % 5)
            classes.append({
                "id": class_id,
                "label": class_label(grade, section),
                "grade": grade,
                "student_count": student_count,
                "shift_id": "morning",
            })
            teachers.append({
                "id": teacher_id,
                "label": f"Teacher T-{grade}{SECTION_LABELS[section]}",
                "qualified_subject_ids": all_subject_ids,
            })
            classrooms.append({
                "id": room_id,
                "label": f"Room {grade}{SECTION_LABELS[section]}",
                "capacity": 30,
                "capabilities": ["general", "sports", "physics_lab", "chemistry_lab", "computer_lab", "workshop", "art"],
            })
            daily_limits.extend([
                {"resource": {"type": "class", "id": class_id}, "maximum": 6 if grade <= 6 else 7},
                {"resource": {"type": "teacher", "id": teacher_id}, "maximum": 6 if grade <= 6 else 7},
            ])
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
                eligible_teacher_ids = [teacher_id]
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

    teachers.extend([
        {"id": "t_science", "label": "Teacher T-Science", "qualified_subject_ids": ["physics", "chemistry"]},
        {"id": "t_english_a", "label": "Teacher T-English-A", "qualified_subject_ids": ["english"]},
        {"id": "t_english_b", "label": "Teacher T-English-B", "qualified_subject_ids": ["english"]},
        {"id": "t_history", "label": "Teacher T-History", "qualified_subject_ids": ["art"]},
    ])
    classrooms.extend([
        {"id": "science_lab", "label": "Science Laboratory", "capacity": 30, "capabilities": ["general", "physics_lab", "chemistry_lab"]},
        {"id": "hall", "label": "Assembly Hall", "capacity": 60, "capabilities": ["assembly"]},
        {"id": "language_room_a", "label": "Language Room A", "capacity": 30, "capabilities": ["general"]},
        {"id": "language_room_b", "label": "Language Room B", "capacity": 30, "capabilities": ["general"]},
    ])

    resource_availability.extend([
        {"resource": {"type": "teacher", "id": "t_math"}, "unavailable_slots": [], "preferred_slots": []},
        {"resource": {"type": "teacher", "id": "t_7a"}, "unavailable_slots": [], "preferred_slots": []},
        {"resource": {"type": "classroom", "id": "science_lab"}, "unavailable_slots": [{"day_id": "fri", "period_id": "p6"}], "preferred_slots": []},
    ])

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
        "fixed_lessons": [{"id": "fixed_joint_advisory", "requirement_id": "req_joint_advisory", "occurrence_index": 0, "slot": {"day_id": "mon", "period_id": "p1"}, "teacher_id": "t_7a", "classroom_id": "room_7a"}],
        "policies": {
            "daily_limits": daily_limits,
            "difficult_load_targets": difficult_targets,
            "soft_constraint_weights": [
                {"constraint_id": "SC-001", "priority": "P1", "weight": 10},
                {"constraint_id": "SC-002", "priority": "P1", "weight": 40},
                {"constraint_id": "SC-003", "priority": "P1", "weight": 200},
                {"constraint_id": "SC-004", "priority": "P2", "weight": 3},
                {"constraint_id": "SC-005", "priority": "P2", "weight": 4},
            ],
        },
        "timetable_versions": [],
    }


if __name__ == "__main__":
    OUTPUT.write_text(json.dumps(build(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT}")
