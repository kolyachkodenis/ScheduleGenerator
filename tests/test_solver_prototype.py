from __future__ import annotations

import copy
import json
import unittest

from schedule_generator import (
    GenerationOptions,
    GenerationStatus,
    SchedulingProblem,
    generate_schedule,
)
from schedule_generator.prototype import ROOT
from schedule_generator.quality import evaluate_quality
from scripts.benchmark_solver import build_dataset


EXAMPLE_PATH = ROOT / "examples" / "small-school.json"


def load_example() -> dict:
    return json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))


class SolverPrototypeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.expectations = json.loads(
            (ROOT / "tests" / "reference" / "small-school.expectations.json").read_text(
                encoding="utf-8"
            )
        )
        cls.problem = SchedulingProblem.from_mapping(load_example())
        cls.typed_result = generate_schedule(
            cls.problem,
            GenerationOptions(time_limit_seconds=10, seed=1, workers=1),
        )
        cls.result = cls.typed_result.to_dict()

    def test_example_produces_verified_timetable(self) -> None:
        self.assertIn(self.result["status"], self.expectations["allowed_statuses"])
        self.assertEqual(
            len(self.result["validation_errors"]),
            self.expectations["validation_error_count"],
        )
        self.assertEqual(
            len(self.result["assignments"]), self.expectations["assignment_count"]
        )
        self.assertEqual(
            {
                item["constraint_id"]
                for item in self.result["quality_report"]["violations"]
            }.issubset(set(self.expectations["quality_constraint_ids"])),
            True,
        )

    def test_fixed_lesson_is_preserved(self) -> None:
        assignment = next(
            item
            for item in self.result["assignments"]
            if item["requirement_id"] == "req_joint_advisory"
        )
        self.assertEqual(assignment["slot"], {"day_id": "mon", "period_id": "p1"})
        self.assertEqual(assignment["teacher_id"], "t_7a")
        self.assertEqual(assignment["classroom_id"], "room_7a")

    def test_class_timetables_have_expected_daily_loads_without_gaps(self) -> None:
        dataset = load_example()
        requirements = {
            item["id"]: item for item in dataset["curriculum_requirements"]
        }
        period_ordinals = {
            item["id"]: item["ordinal"] for item in dataset["academic_period"]["periods"]
        }
        expected_by_grade = {
            5: [6, 6, 6, 6, 5],
            6: [6, 6, 6, 6, 6],
            7: [6, 6, 7, 6, 6],
            8: [7, 7, 7, 6, 6],
            9: [7, 7, 7, 6, 6],
            10: [7, 7, 6, 6, 6],
            11: [7, 7, 6, 6, 6],
        }
        for class_item in dataset["classes"]:
            occupied_by_day = {day["id"]: set() for day in dataset["academic_period"]["days"]}
            for assignment in self.result["assignments"]:
                requirement = requirements[assignment["requirement_id"]]
                if requirement["participant"] != {"type": "class", "id": class_item["id"]}:
                    continue
                occupied_by_day[assignment["slot"]["day_id"]].update(
                    period_ordinals[period_id]
                    for period_id in assignment["occupied_period_ids"]
                )
            daily_loads = [len(periods) for periods in occupied_by_day.values()]
            self.assertEqual(daily_loads, expected_by_grade[class_item["grade"]])
            self.assertTrue(
                all(
                    not periods or max(periods) - min(periods) + 1 == len(periods)
                    for periods in occupied_by_day.values()
                )
            )

    def test_public_result_contains_quality_report_and_fingerprint(self) -> None:
        self.assertEqual(
            self.typed_result.dataset_fingerprint,
            self.problem.fingerprint,
        )
        self.assertIsNotNone(self.typed_result.quality)
        self.assertEqual(
            self.typed_result.quality.total_penalty,
            sum(
                item.weighted_penalty
                for item in self.typed_result.quality.by_constraint
            ),
        )
        self.assertEqual(
            self.typed_result.quality.total_penalty,
            int(self.typed_result.solver.objective),
        )
        self.assertEqual(
            self.typed_result.quality.total_penalty,
            sum(
                item.weighted_penalty
                for item in self.typed_result.quality.violations
            ),
        )
        self.assertEqual(self.typed_result.solver.seed, 1)
        self.assertEqual(self.typed_result.solver.workers, 1)
        self.assertEqual(self.typed_result.solver.time_limit_seconds, 10)

    def test_manual_quality_evaluator_matches_solver_result(self) -> None:
        report = evaluate_quality(load_example(), self.result["assignments"])
        self.assertEqual(
            report["total_penalty"],
            self.result["quality_report"]["total_penalty"],
        )

    def test_problem_fingerprint_is_independent_of_key_order(self) -> None:
        dataset = load_example()
        reversed_dataset = dict(reversed(list(dataset.items())))
        other = SchedulingProblem.from_mapping(reversed_dataset)

        self.assertEqual(self.problem.fingerprint, other.fingerprint)

    def test_fully_unavailable_teacher_reports_input_infeasibility(self) -> None:
        dataset = copy.deepcopy(load_example())
        overlay = json.loads(
            (ROOT / "tests" / "reference" / "teacher-unavailable.overlay.json").read_text(
                encoding="utf-8"
            )
        )
        all_slots = [
            {"day_id": day["id"], "period_id": period["id"]}
            for day in dataset["academic_period"]["days"]
            for period in dataset["academic_period"]["periods"]
        ]
        availability = next(
            item
            for item in dataset["resource_availability"]
            if item["resource"] == overlay["resource"]
        )
        availability["unavailable_slots"] = all_slots
        availability["preferred_slots"] = []

        result = generate_schedule(
            dataset, GenerationOptions(time_limit_seconds=1)
        ).to_dict()

        self.assertEqual(result["status"], overlay["expected_status"])
        self.assertTrue(
            any(
                item["code"] == overlay["expected_diagnostic_code"]
                for item in result["diagnostics"]
            )
        )

    def test_invalid_dataset_returns_actionable_status(self) -> None:
        dataset = load_example()
        dataset["subjects"] = [
            item for item in dataset["subjects"] if item["id"] != "mathematics"
        ]

        result = generate_schedule(dataset, GenerationOptions(time_limit_seconds=1))

        self.assertEqual(result.status, GenerationStatus.INVALID_INPUT)
        self.assertTrue(result.diagnostics)
        self.assertTrue(
            any("mathematics" in diagnostic.message for diagnostic in result.diagnostics)
        )

    def test_small_run_is_reproducible_with_one_worker(self) -> None:
        problem = SchedulingProblem.from_mapping(build_dataset(2))
        options = GenerationOptions(time_limit_seconds=5, seed=7, workers=1)

        first = generate_schedule(problem, options)
        second = generate_schedule(problem, options)

        self.assertEqual(first.status, GenerationStatus.OPTIMAL)
        self.assertEqual(second.status, GenerationStatus.OPTIMAL)
        self.assertEqual(first.assignments, second.assignments)
        self.assertEqual(first.quality, second.quality)


class GenerationOptionsTests(unittest.TestCase):
    def test_invalid_limits_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "greater than zero"):
            GenerationOptions(time_limit_seconds=0)
        with self.assertRaisesRegex(ValueError, "non-negative"):
            GenerationOptions(seed=-1)
        with self.assertRaisesRegex(ValueError, "at least one"):
            GenerationOptions(workers=0)


if __name__ == "__main__":
    unittest.main()
