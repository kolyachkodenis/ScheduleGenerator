from __future__ import annotations

import json
import unittest

from hypothesis import given, settings, strategies as st

from schedule_generator import SchedulingProblem
from schedule_generator.prototype import ROOT, PrototypeBuilder, verify_solution
from scripts.validate_dataset import SemanticValidator
from scenario_factory import fixed_lesson_dataset
from test_hard_constraints import assignment_for, occurrence


def load_example() -> dict:
    return json.loads(
        (ROOT / "examples" / "small-school.json").read_text(encoding="utf-8")
    )


PROPERTY_SETTINGS = settings(max_examples=25, deadline=None, derandomize=True)


class PropertyTests(unittest.TestCase):
    @PROPERTY_SETTINGS
    @given(st.permutations(tuple(load_example().keys())))
    def test_problem_fingerprint_is_stable_for_all_top_level_key_orders(
        self, order
    ) -> None:
        dataset = load_example()
        reordered = {key: dataset[key] for key in order}
        self.assertEqual(
            SchedulingProblem.from_mapping(dataset).fingerprint,
            SchedulingProblem.from_mapping(reordered).fingerprint,
        )

    @PROPERTY_SETTINGS
    @given(
        class_size=st.integers(min_value=2, max_value=50),
        first_group=st.integers(min_value=1, max_value=50),
        second_group=st.integers(min_value=1, max_value=50),
    )
    def test_complete_partition_is_valid_exactly_when_group_total_matches_class(
        self, class_size: int, first_group: int, second_group: int
    ) -> None:
        dataset = load_example()
        dataset["classes"][0]["student_count"] = class_size
        dataset["groups"][0]["student_count"] = first_group
        dataset["groups"][1]["student_count"] = second_group

        errors = SemanticValidator(dataset).validate()
        partition_errors = [
            error
            for error in errors
            if "$.group_partitions[partition_7a_english]" in error
        ]

        self.assertIs(
            bool(partition_errors), first_group + second_group != class_size
        )

    @PROPERTY_SETTINGS
    @given(
        block_length=st.integers(min_value=1, max_value=4),
        occurrence_count=st.integers(min_value=1, max_value=10),
    )
    def test_required_lesson_count_always_expands_to_exact_occurrences(
        self, block_length: int, occurrence_count: int
    ) -> None:
        dataset = fixed_lesson_dataset([("mon", "p1")])
        requirement = dataset["curriculum_requirements"][0]
        requirement["weekly_lessons"] = block_length * occurrence_count
        requirement["block_length"] = block_length
        dataset["fixed_lessons"] = []

        builder = PrototypeBuilder(dataset)

        self.assertEqual(len(builder.occurrences), occurrence_count)

    @PROPERTY_SETTINGS
    @given(first_index=st.integers(0, 3), second_index=st.integers(0, 3))
    def test_any_two_distinct_math_occurrences_collide_in_the_same_candidate(
        self, first_index: int, second_index: int
    ) -> None:
        if first_index == second_index:
            return
        dataset = load_example()
        builder = PrototypeBuilder(dataset)
        first = occurrence(builder, "req_7a_math", first_index)
        second = occurrence(builder, "req_7a_math", second_index)
        candidate = builder.enumerate_candidates(first)[0]

        errors = verify_solution(
            dataset,
            [assignment_for(first, candidate), assignment_for(second, candidate)],
        )

        self.assertTrue(
            any("Resource collision ('student'" in error for error in errors)
        )


if __name__ == "__main__":
    unittest.main()
