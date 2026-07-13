from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.validate_dataset import ROOT, SemanticValidator


EXAMPLE_PATH = ROOT / "examples" / "small-school.json"


def load_example() -> dict:
    return json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))


class SemanticValidatorTests(unittest.TestCase):
    def assert_has_error(self, dataset: dict, expected: str) -> None:
        errors = SemanticValidator(dataset).validate()
        self.assertTrue(
            any(expected in error for error in errors),
            f"Expected an error containing {expected!r}, got: {errors}",
        )

    def test_synthetic_example_is_semantically_valid(self) -> None:
        self.assertEqual(SemanticValidator(load_example()).validate(), [])

    def test_duplicate_identifier_is_rejected(self) -> None:
        dataset = load_example()
        duplicate = copy.deepcopy(dataset["teachers"][0])
        dataset["teachers"].append(duplicate)

        self.assert_has_error(dataset, "duplicate ID 't_math'")

    def test_unknown_teacher_reference_is_rejected(self) -> None:
        dataset = load_example()
        dataset["curriculum_requirements"][0]["eligible_teacher_ids"] = [
            "t_missing"
        ]

        self.assert_has_error(dataset, "unknown teachers ID 't_missing'")

    def test_incomplete_complete_partition_is_rejected(self) -> None:
        dataset = load_example()
        dataset["groups"][0]["student_count"] = 11

        self.assert_has_error(dataset, "complete partition totals 23, expected 24")

    def test_unsuitable_allowed_classroom_is_rejected(self) -> None:
        dataset = load_example()
        physics = next(
            requirement
            for requirement in dataset["curriculum_requirements"]
            if requirement["id"] == "req_7a_physics"
        )
        physics["allowed_classroom_ids"] = ["room_101"]

        self.assert_has_error(
            dataset,
            "no candidate classroom satisfies required capabilities and capacity",
        )

    def test_unknown_constraint_weight_is_rejected(self) -> None:
        dataset = load_example()
        dataset["policies"]["soft_constraint_weights"][0]["constraint_id"] = "SC-999"

        self.assert_has_error(dataset, "constraint ID 'SC-999' is not in the catalog")


if __name__ == "__main__":
    unittest.main()
