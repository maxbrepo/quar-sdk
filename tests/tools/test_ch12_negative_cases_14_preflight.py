"""Regression tests for intentionally failing Chapter 12 programs."""

import unittest
from pathlib import Path

from main import execute_regression_source, extract_test_number


ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "examples" / "0.0.4" / "typed" / "12 error handling"
NEGATIVE_CASES = {225, 226, 227, 228, 229, 232, 233}


class Chapter12NegativeCasesTest(unittest.TestCase):
    def test_expected_failures_are_not_crashes(self):
        sources = {
            extract_test_number(path): path
            for path in EXAMPLES.glob("*.vq")
            if extract_test_number(path) in NEGATIVE_CASES
        }
        self.assertEqual(set(sources), NEGATIVE_CASES)
        for number, source in sorted(sources.items()):
            with self.subTest(number=number):
                status, message = execute_regression_source(source)
                self.assertEqual(status, "EXPECTED ERROR", message)


if __name__ == "__main__":
    unittest.main()
