from __future__ import annotations

import json
import unittest

from schedule_generator.prototype import (
    ROOT,
    PrototypeBuilder,
    solve_dataset,
    verify_solution,
)
from scenario_factory import fixed_lesson_dataset


def load_example() -> dict:
    return json.loads(
        (ROOT / "examples" / "small-school.json").read_text(encoding="utf-8")
    )


def occurrence(builder: PrototypeBuilder, requirement_id: str, index: int = 0):
    return next(
        item
        for item in builder.occurrences
        if item.requirement_id == requirement_id and item.index == index
    )


def assignment_for(occurrence_item, candidate) -> dict:
    return {
        "id": occurrence_item.id,
        "requirement_id": occurrence_item.requirement_id,
        "occurrence_index": occurrence_item.index,
        "slot": {
            "day_id": candidate.day_id,
            "period_id": candidate.start_period_id,
        },
        "occupied_period_ids": [
            period_id for _day_id, period_id in candidate.occupied_slots
        ],
        "teacher_id": candidate.teacher_id,
        "classroom_id": candidate.classroom_id,
    }


class HardConstraintTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dataset = load_example()
        self.builder = PrototypeBuilder(self.dataset)

    def same_candidate_math_conflict(self) -> list[str]:
        first = occurrence(self.builder, "req_7a_math", 0)
        second = occurrence(self.builder, "req_7a_math", 1)
        candidate = self.builder.enumerate_candidates(first)[0]
        assignments = [
            assignment_for(first, candidate),
            assignment_for(second, candidate),
        ]
        return verify_solution(self.dataset, assignments)

    def test_hc001_required_lesson_coverage_creates_exact_occurrences(self) -> None:
        counts = {}
        for item in self.builder.occurrences:
            counts[item.requirement_id] = counts.get(item.requirement_id, 0) + 1
        for requirement in self.dataset["curriculum_requirements"]:
            self.assertEqual(
                counts[requirement["id"]],
                requirement["weekly_lessons"] // requirement["block_length"],
            )

    def test_hc002_class_non_overlap_is_detected(self) -> None:
        self.assertTrue(
            any("Resource collision ('student'" in error for error in self.same_candidate_math_conflict())
        )

    def test_hc003_group_non_overlap_is_detected(self) -> None:
        first = occurrence(self.builder, "req_7a_en_1", 0)
        second = occurrence(self.builder, "req_7a_en_1", 1)
        candidate = self.builder.enumerate_candidates(first)[0]
        errors = verify_solution(
            self.dataset,
            [assignment_for(first, candidate), assignment_for(second, candidate)],
        )
        self.assertTrue(
            any("group:group_7a_en_1" in error for error in errors), errors
        )

    def test_hc004_teacher_non_overlap_is_detected(self) -> None:
        self.assertTrue(
            any("Resource collision ('teacher'" in error for error in self.same_candidate_math_conflict())
        )

    def test_hc005_classroom_non_overlap_is_detected(self) -> None:
        self.assertTrue(
            any("Resource collision ('classroom'" in error for error in self.same_candidate_math_conflict())
        )

    def test_hc006_candidates_stay_within_class_shift(self) -> None:
        self.builder.shifts["morning"]["period_ids"] = ["p2", "p3"]
        item = occurrence(self.builder, "req_7a_math")
        candidates = self.builder.enumerate_candidates(item)
        self.assertTrue(candidates)
        self.assertEqual(
            {
                period_id
                for candidate in candidates
                for _day_id, period_id in candidate.occupied_slots
            },
            {"p2", "p3"},
        )

    def test_hc007_teacher_unavailability_removes_candidates(self) -> None:
        self.builder.availability[("teacher", "t_7a")]["unavailable"].add(("tue", "p1"))
        item = occurrence(self.builder, "req_7a_math")
        candidates = self.builder.enumerate_candidates(item)
        self.assertNotIn(
            ("tue", "p1"),
            {(candidate.day_id, candidate.start_period_id) for candidate in candidates},
        )

    def test_hc008_classroom_unavailability_removes_candidates(self) -> None:
        self.builder.availability[("classroom", "room_7a")] = {
            "unavailable": {("fri", "p6")},
            "preferred": set(),
        }
        item = occurrence(self.builder, "req_7a_physics")
        candidates = self.builder.enumerate_candidates(item)
        self.assertNotIn(
            ("fri", "p6"),
            {(candidate.day_id, candidate.start_period_id) for candidate in candidates},
        )

    def test_hc009_fixed_lesson_has_only_fixed_candidates(self) -> None:
        item = occurrence(self.builder, "req_joint_advisory")
        candidates = self.builder.enumerate_candidates(item)
        self.assertEqual(len(candidates), 1)
        candidate = candidates[0]
        self.assertEqual(
            (
                candidate.day_id,
                candidate.start_period_id,
                candidate.teacher_id,
                candidate.classroom_id,
            ),
            ("mon", "p1", "t_7a", "room_7a"),
        )

    def test_hc010_only_eligible_teachers_receive_candidates(self) -> None:
        item = occurrence(self.builder, "req_8a_english")
        candidates = self.builder.enumerate_candidates(item)
        self.assertEqual(
            {candidate.teacher_id for candidate in candidates},
            {"t_8a"},
        )

    def test_hc011_room_capability_filters_candidates(self) -> None:
        item = occurrence(self.builder, "req_7a_physics")
        candidates = self.builder.enumerate_candidates(item)
        self.assertEqual({candidate.classroom_id for candidate in candidates}, {"room_7a"})

    def test_hc012_room_capacity_filters_candidates(self) -> None:
        self.builder.rooms["room_7a"]["capacity"] = 20
        item = occurrence(self.builder, "req_7a_physics")
        self.assertEqual(self.builder.enumerate_candidates(item), [])

    def test_hc013_split_groups_are_disjoint_and_cover_whole_class(self) -> None:
        class_atoms = self.builder.student_atoms({"type": "class", "id": "class_7a"})
        group_1 = self.builder.student_atoms(
            {"type": "group", "id": "group_7a_en_1"}
        )
        group_2 = self.builder.student_atoms(
            {"type": "group", "id": "group_7a_en_2"}
        )
        self.assertTrue(group_1.isdisjoint(group_2))
        self.assertEqual(class_atoms, group_1 | group_2)

    def test_hc014_cohort_occupies_every_member_class(self) -> None:
        atoms = self.builder.student_atoms(
            {"type": "cohort", "id": "cohort_7a_8a_advisory"}
        )
        self.assertEqual(
            atoms,
            {
                "group:group_7a_en_1",
                "group:group_7a_en_2",
                "class:class_8a",
            },
        )

    def test_hc015_daily_class_limit_can_make_model_infeasible(self) -> None:
        dataset = fixed_lesson_dataset(
            [("mon", "p1"), ("mon", "p2")],
            class_daily_limit=1,
            teacher_daily_limit=4,
        )
        self.assertEqual(solve_dataset(dataset, time_limit=2)["status"], "INFEASIBLE")

    def test_hc016_daily_teacher_limit_can_make_model_infeasible(self) -> None:
        dataset = fixed_lesson_dataset(
            [("mon", "p1"), ("mon", "p2")],
            class_daily_limit=4,
            teacher_daily_limit=1,
        )
        self.assertEqual(solve_dataset(dataset, time_limit=2)["status"], "INFEASIBLE")

    def test_hc017_block_candidates_use_consecutive_periods(self) -> None:
        item = occurrence(self.builder, "req_8a_chemistry")
        candidates = self.builder.enumerate_candidates(item)
        self.assertTrue(candidates)
        for candidate in candidates:
            indices = [
                self.builder.period_index[period_id]
                for _day_id, period_id in candidate.occupied_slots
            ]
            self.assertEqual(indices, list(range(indices[0], indices[0] + 2)))


if __name__ == "__main__":
    unittest.main()
