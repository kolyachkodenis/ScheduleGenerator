"""Run reproducible synthetic size benchmarks for the CP-SAT prototype."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from schedule_generator.prototype import solve_dataset  # noqa: E402


def build_dataset(class_count: int) -> dict:
    days = [
        {"id": day_id, "label": label, "ordinal": index}
        for index, (day_id, label) in enumerate(
            (
                ("mon", "Monday"),
                ("tue", "Tuesday"),
                ("wed", "Wednesday"),
                ("thu", "Thursday"),
                ("fri", "Friday"),
            ),
            start=1,
        )
    ]
    periods = [
        {
            "id": f"p{index}",
            "label": f"Period {index}",
            "ordinal": index,
            "start_time": f"{7 + index:02d}:00",
            "end_time": f"{7 + index:02d}:45",
        }
        for index in range(1, 7)
    ]

    classes = [
        {
            "id": f"class_{index:02d}",
            "label": f"Synthetic Class {index:02d}",
            "grade": 7 + (index % 2),
            "student_count": 24,
            "shift_id": "morning",
        }
        for index in range(1, class_count + 1)
    ]
    teacher_pairs = math.ceil(class_count / 2)
    teachers = []
    for pair in range(1, teacher_pairs + 1):
        teachers.extend(
            [
                {
                    "id": f"t_math_{pair:02d}",
                    "label": f"Synthetic Mathematics Teacher {pair:02d}",
                    "qualified_subject_ids": ["mathematics"],
                },
                {
                    "id": f"t_history_{pair:02d}",
                    "label": f"Synthetic History Teacher {pair:02d}",
                    "qualified_subject_ids": ["history"],
                },
            ]
        )
    teachers.append(
        {
            "id": "t_pe",
            "label": "Synthetic Physical Education Teacher",
            "qualified_subject_ids": ["physical_education"],
        }
    )

    general_room_count = max(1, math.ceil(class_count / 2))
    classrooms = [
        {
            "id": f"room_{index:02d}",
            "label": f"Synthetic Room {index:02d}",
            "capacity": 30,
            "capabilities": ["general"],
        }
        for index in range(1, general_room_count + 1)
    ]
    classrooms.append(
        {
            "id": "gym",
            "label": "Synthetic Gymnasium",
            "capacity": 60,
            "capabilities": ["sports"],
        }
    )

    requirements = []
    daily_limits = []
    difficult_targets = []
    for index, class_record in enumerate(classes, start=1):
        pair = math.ceil(index / 2)
        for subject_id, weekly_lessons, teacher_id, capability, room_ids in (
            (
                "mathematics",
                4,
                f"t_math_{pair:02d}",
                "general",
                [f"room_{pair:02d}"],
            ),
            (
                "history",
                2,
                f"t_history_{pair:02d}",
                "general",
                [f"room_{pair:02d}"],
            ),
            ("physical_education", 2, "t_pe", "sports", ["gym"]),
        ):
            requirements.append(
                {
                    "id": f"req_{class_record['id']}_{subject_id}",
                    "participant": {"type": "class", "id": class_record["id"]},
                    "subject_id": subject_id,
                    "eligible_teacher_ids": [teacher_id],
                    "weekly_lessons": weekly_lessons,
                    "block_length": 1,
                    "required_room_capabilities": [capability],
                    "allowed_classroom_ids": room_ids,
                }
            )
        daily_limits.append(
            {
                "resource": {"type": "class", "id": class_record["id"]},
                "maximum": 6,
            }
        )
        difficult_targets.append(
            {
                "participant": {"type": "class", "id": class_record["id"]},
                "target": 6,
            }
        )

    return {
        "schema_version": "0.1.0",
        "dataset_id": f"benchmark_{class_count}_classes",
        "school": {
            "id": "benchmark_school",
            "label": "Synthetic Benchmark School",
            "timezone": "Europe/Minsk",
        },
        "academic_period": {
            "id": "benchmark_term",
            "label": "Synthetic Benchmark Term",
            "start_date": "2026-09-01",
            "end_date": "2026-12-24",
            "days": days,
            "periods": periods,
            "shifts": [
                {
                    "id": "morning",
                    "label": "Morning shift",
                    "period_ids": [period["id"] for period in periods],
                }
            ],
        },
        "subjects": [
            {"id": "mathematics", "label": "Mathematics", "default_workload": 3},
            {"id": "history", "label": "History", "default_workload": 2},
            {
                "id": "physical_education",
                "label": "Physical Education",
                "default_workload": 1,
            },
        ],
        "teachers": teachers,
        "classrooms": classrooms,
        "classes": classes,
        "group_partitions": [],
        "groups": [],
        "cohorts": [],
        "curriculum_requirements": requirements,
        "resource_availability": [],
        "fixed_lessons": [],
        "policies": {
            "daily_limits": daily_limits,
            "difficult_load_targets": difficult_targets,
            "soft_constraint_weights": [
                {"constraint_id": "SC-001", "priority": "P1", "weight": 10},
                {"constraint_id": "SC-002", "priority": "P2", "weight": 4},
                {"constraint_id": "SC-003", "priority": "P1", "weight": 8},
                {"constraint_id": "SC-004", "priority": "P2", "weight": 3},
                {"constraint_id": "SC-005", "priority": "P2", "weight": 4},
            ],
        },
        "timetable_versions": [],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", nargs="+", type=int, default=[2, 6, 11])
    parser.add_argument("--time-limit", type=float, default=5.0)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--json", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    results = []
    for class_count in args.sizes:
        result = solve_dataset(
            build_dataset(class_count),
            time_limit=args.time_limit,
            seed=args.seed,
            workers=1,
        )
        solver = result.get("solver", {})
        row = {
            "classes": class_count,
            "status": result["status"],
            "assignments": len(result["assignments"]),
            "variables": solver.get("variables"),
            "constraints": solver.get("constraints"),
            "objective": solver.get("objective"),
            "wall_time_seconds": solver.get("wall_time_seconds"),
            "verified": not result["validation_errors"]
            and result["status"] in {"OPTIMAL", "FEASIBLE"},
        }
        results.append(row)
        print(json.dumps(row, sort_keys=True))
    if args.json:
        args.json.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    return 0 if all(row["verified"] for row in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
