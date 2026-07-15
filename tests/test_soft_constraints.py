from __future__ import annotations

import unittest

from schedule_generator import GenerationOptions, GenerationStatus, generate_schedule
from scenario_factory import fixed_lesson_dataset


def solve_penalty(dataset: dict, constraint_id: str) -> tuple[int, int, int]:
    result = generate_schedule(
        dataset,
        GenerationOptions(time_limit_seconds=2, seed=1, workers=1),
    )
    if result.status is not GenerationStatus.OPTIMAL:
        raise AssertionError(f"Expected OPTIMAL, received {result.status}: {result.diagnostics}")
    quality = next(
        item for item in result.quality.by_constraint if item.constraint_id == constraint_id
    )
    return quality.raw_penalty, quality.weighted_penalty, result.quality.total_penalty


class SoftConstraintTests(unittest.TestCase):
    def test_sc001_difficult_subject_overload_penalty(self) -> None:
        dataset = fixed_lesson_dataset(
            [("mon", "p1"), ("mon", "p2")],
            constraint_id="SC-001",
            weight=10,
            difficult_target=3,
            same_subject=False,
        )
        self.assertEqual(solve_penalty(dataset, "SC-001"), (3, 30, 30))

    def test_sc002_daily_load_spread_penalty(self) -> None:
        dataset = fixed_lesson_dataset(
            [("mon", "p1"), ("mon", "p2")],
            constraint_id="SC-002",
            weight=4,
            same_subject=False,
        )
        self.assertEqual(solve_penalty(dataset, "SC-002"), (2, 8, 8))

    def test_sc003_class_gap_penalty(self) -> None:
        dataset = fixed_lesson_dataset(
            [("mon", "p1"), ("mon", "p3")],
            constraint_id="SC-003",
            weight=8,
            same_subject=False,
        )
        self.assertEqual(solve_penalty(dataset, "SC-003"), (1, 8, 8))

    def test_sc004_teacher_gap_penalty(self) -> None:
        dataset = fixed_lesson_dataset(
            [("mon", "p1"), ("mon", "p3")],
            constraint_id="SC-004",
            weight=3,
            same_subject=False,
        )
        self.assertEqual(solve_penalty(dataset, "SC-004"), (1, 3, 3))

    def test_sc005_same_day_subject_spread_penalty(self) -> None:
        dataset = fixed_lesson_dataset(
            [("mon", "p1"), ("mon", "p2")],
            constraint_id="SC-005",
            weight=4,
            same_subject=True,
        )
        self.assertEqual(solve_penalty(dataset, "SC-005"), (1, 4, 4))

    def test_sc007_teacher_preference_penalty(self) -> None:
        dataset = fixed_lesson_dataset(
            [("mon", "p2")],
            constraint_id="SC-007",
            weight=5,
            preferred_slots=[("mon", "p1")],
        )
        self.assertEqual(solve_penalty(dataset, "SC-007"), (1, 5, 5))

    def test_sc019_related_language_subjects_prefer_the_same_day(self) -> None:
        dataset = fixed_lesson_dataset(
            [("mon", "p1"), ("tue", "p1")],
            constraint_id="SC-019",
            weight=3,
            same_subject=False,
        )
        replacements = {
            "subject_0": "russian_language",
            "subject_1": "russian_literature",
        }
        for subject in dataset["subjects"]:
            subject["id"] = replacements[subject["id"]]
        for requirement in dataset["curriculum_requirements"]:
            requirement["subject_id"] = replacements[requirement["subject_id"]]
        dataset["teachers"][0]["qualified_subject_ids"] = list(
            replacements.values()
        )
        self.assertEqual(solve_penalty(dataset, "SC-019"), (2, 6, 6))


if __name__ == "__main__":
    unittest.main()
