"""Synthetic dataset builders shared by scheduling-core tests."""

from __future__ import annotations

from typing import Iterable


def fixed_lesson_dataset(
    starts: Iterable[tuple[str, str]],
    *,
    constraint_id: str | None = None,
    weight: int = 1,
    difficult_target: int = 100,
    same_subject: bool = True,
    preferred_slots: Iterable[tuple[str, str]] = (),
    class_daily_limit: int = 4,
    teacher_daily_limit: int = 4,
) -> dict:
    starts = list(starts)
    preferred_slots = list(preferred_slots)
    subject_ids = ["subject_main"] if same_subject else [
        f"subject_{index}" for index in range(len(starts))
    ]
    subjects = [
        {
            "id": subject_id,
            "label": f"Synthetic Subject {index + 1}",
            "default_workload": 3,
        }
        for index, subject_id in enumerate(subject_ids)
    ]
    requirements = []
    fixed_lessons = []
    for index, (day_id, period_id) in enumerate(starts):
        subject_id = "subject_main" if same_subject else f"subject_{index}"
        requirement_id = f"req_{index}"
        requirements.append(
            {
                "id": requirement_id,
                "participant": {"type": "class", "id": "class_a"},
                "subject_id": subject_id,
                "eligible_teacher_ids": ["teacher_a"],
                "weekly_lessons": 1,
                "block_length": 1,
                "required_room_capabilities": ["general"],
                "allowed_classroom_ids": ["room_a"],
            }
        )
        fixed_lessons.append(
            {
                "id": f"fixed_{index}",
                "requirement_id": requirement_id,
                "occurrence_index": 0,
                "slot": {"day_id": day_id, "period_id": period_id},
                "teacher_id": "teacher_a",
                "classroom_id": "room_a",
            }
        )

    weights = []
    if constraint_id:
        weights.append(
            {
                "constraint_id": constraint_id,
                "priority": "P1",
                "weight": weight,
            }
        )

    availability = []
    if preferred_slots:
        availability.append(
            {
                "resource": {"type": "teacher", "id": "teacher_a"},
                "unavailable_slots": [],
                "preferred_slots": [
                    {"day_id": day_id, "period_id": period_id}
                    for day_id, period_id in preferred_slots
                ],
            }
        )

    return {
        "schema_version": "0.1.0",
        "dataset_id": "fixed_lesson_test",
        "school": {
            "id": "test_school",
            "label": "Synthetic Test School",
            "timezone": "Europe/Minsk",
        },
        "academic_period": {
            "id": "test_term",
            "label": "Synthetic Test Term",
            "start_date": "2026-09-01",
            "end_date": "2026-12-24",
            "days": [
                {"id": "mon", "label": "Monday", "ordinal": 1},
                {"id": "tue", "label": "Tuesday", "ordinal": 2},
                {"id": "wed", "label": "Wednesday", "ordinal": 3},
                {"id": "thu", "label": "Thursday", "ordinal": 4},
                {"id": "fri", "label": "Friday", "ordinal": 5},
            ],
            "periods": [
                {
                    "id": f"p{index}",
                    "label": f"Period {index}",
                    "ordinal": index,
                    "start_time": f"{7 + index:02d}:00",
                    "end_time": f"{7 + index:02d}:45",
                }
                for index in range(1, 5)
            ],
            "shifts": [
                {
                    "id": "morning",
                    "label": "Morning shift",
                    "period_ids": ["p1", "p2", "p3", "p4"],
                }
            ],
        },
        "subjects": subjects,
        "teachers": [
            {
                "id": "teacher_a",
                "label": "Synthetic Teacher A",
                "qualified_subject_ids": subject_ids,
            }
        ],
        "classrooms": [
            {
                "id": "room_a",
                "label": "Synthetic Room A",
                "capacity": 30,
                "capabilities": ["general"],
            }
        ],
        "classes": [
            {
                "id": "class_a",
                "label": "Synthetic Class A",
                "grade": 7,
                "student_count": 20,
                "shift_id": "morning",
            }
        ],
        "group_partitions": [],
        "groups": [],
        "cohorts": [],
        "curriculum_requirements": requirements,
        "resource_availability": availability,
        "fixed_lessons": fixed_lessons,
        "policies": {
            "daily_limits": [
                {
                    "resource": {"type": "class", "id": "class_a"},
                    "maximum": class_daily_limit,
                },
                {
                    "resource": {"type": "teacher", "id": "teacher_a"},
                    "maximum": teacher_daily_limit,
                },
            ],
            "difficult_load_targets": [
                {
                    "participant": {"type": "class", "id": "class_a"},
                    "target": difficult_target,
                }
            ],
            "soft_constraint_weights": weights,
        },
        "timetable_versions": [],
    }
