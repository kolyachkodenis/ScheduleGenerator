from __future__ import annotations

import copy
import json
import unittest

from schedule_generator.prototype import ROOT, solve_dataset


EXAMPLE_PATH = ROOT / "examples" / "small-school.json"


def load_example() -> dict:
    return json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))


class SolverPrototypeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = solve_dataset(load_example(), time_limit=10, seed=1, workers=1)

    def test_example_produces_verified_timetable(self) -> None:
        self.assertIn(self.result["status"], {"OPTIMAL", "FEASIBLE"})
        self.assertEqual(self.result["validation_errors"], [])
        self.assertEqual(len(self.result["assignments"]), 27)

    def test_fixed_lesson_is_preserved(self) -> None:
        assignment = next(
            item
            for item in self.result["assignments"]
            if item["requirement_id"] == "req_joint_advisory"
        )
        self.assertEqual(assignment["slot"], {"day_id": "mon", "period_id": "p1"})
        self.assertEqual(assignment["teacher_id"], "t_history")
        self.assertEqual(assignment["classroom_id"], "hall")

    def test_fully_unavailable_teacher_reports_input_infeasibility(self) -> None:
        dataset = copy.deepcopy(load_example())
        all_slots = [
            {"day_id": day["id"], "period_id": period["id"]}
            for day in dataset["academic_period"]["days"]
            for period in dataset["academic_period"]["periods"]
        ]
        availability = next(
            item
            for item in dataset["resource_availability"]
            if item["resource"] == {"type": "teacher", "id": "t_math"}
        )
        availability["unavailable_slots"] = all_slots
        availability["preferred_slots"] = []

        result = solve_dataset(dataset, time_limit=1)

        self.assertEqual(result["status"], "INPUT_INFEASIBLE")
        self.assertTrue(
            any(item["code"] == "NO_CANDIDATE" for item in result["diagnostics"])
        )


if __name__ == "__main__":
    unittest.main()
