from __future__ import annotations

import os
import time
import tracemalloc
import unittest

from schedule_generator.prototype import PrototypeBuilder, solve_dataset
from scripts.benchmark_solver import build_dataset


class ModelScaleRegressionTests(unittest.TestCase):
    def test_large_synthetic_model_stays_within_size_budget(self) -> None:
        artifacts = PrototypeBuilder(build_dataset(11)).build()
        proto = artifacts.model.proto

        self.assertEqual(artifacts.diagnostics, [])
        self.assertLessEqual(len(proto.variables), 6000)
        self.assertLessEqual(len(proto.constraints), 5500)


@unittest.skipUnless(
    os.environ.get("RUN_PERFORMANCE_TESTS") == "1",
    "set RUN_PERFORMANCE_TESTS=1 to run solver performance budgets",
)
class SolverPerformanceBudgetTests(unittest.TestCase):
    CASES = (
        (2, 5.0, 10.0),
        (6, 15.0, 25.0),
        (11, 15.0, 25.0),
    )
    MAX_PYTHON_PEAK_MIB = 512

    def test_small_medium_large_generation_budgets(self) -> None:
        for class_count, solve_limit, elapsed_budget in self.CASES:
            with self.subTest(class_count=class_count):
                tracemalloc.start()
                started = time.perf_counter()
                result = solve_dataset(
                    build_dataset(class_count),
                    time_limit=solve_limit,
                    seed=1,
                    workers=1,
                )
                elapsed = time.perf_counter() - started
                _current, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                peak_mib = peak / (1024 * 1024)

                print(
                    f"performance classes={class_count} status={result['status']} "
                    f"elapsed={elapsed:.3f}s python_peak={peak_mib:.1f}MiB"
                )
                self.assertIn(result["status"], {"OPTIMAL", "FEASIBLE"})
                self.assertEqual(result["validation_errors"], [])
                self.assertLessEqual(elapsed, elapsed_budget)
                self.assertLessEqual(peak_mib, self.MAX_PYTHON_PEAK_MIB)


if __name__ == "__main__":
    unittest.main()
