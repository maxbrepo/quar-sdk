"""Verify regression classifications for static bounds errors and fatal runtime errors."""

import unittest
from pathlib import Path

from main import execute_regression_source


ROOT = Path(__file__).resolve().parents[1] / "examples"


class RegressionRunnerDiagnosticsTests(unittest.TestCase):
    def source_for(self, number):
        matches = list(ROOT.rglob(f"{number} *.vq"))
        self.assertEqual(len(matches), 1, f"Expected one example for {number}")
        return matches[0]

    def test_static_array_bounds_diagnostics(self):
        for number in (115, 116, 124):
            with self.subTest(example=number):
                status, message = execute_regression_source(self.source_for(number))
                self.assertEqual(status, "EXPECTED ERROR")
                self.assertTrue(message.startswith("Array index out of bounds:"))

    def test_assert_panic_and_trace_regression_classifications(self):
        passing = (221, 222, 223, 224, 231)
        expected_errors = (225, 226, 227, 228, 229, 232, 233)
        for number in passing:
            with self.subTest(example=number):
                self.assertEqual(execute_regression_source(self.source_for(number))[0], "PASS")
        for number in expected_errors:
            with self.subTest(example=number):
                self.assertEqual(
                    execute_regression_source(self.source_for(number))[0],
                    "EXPECTED ERROR",
                )


if __name__ == "__main__":
    unittest.main()
