"""Regression coverage for the historical function examples in each profile."""
import unittest
from pathlib import Path
from main import execute_regression_source


class LegacyFunctionProfilesTest(unittest.TestCase):
    def test_function_examples_in_all_profiles(self):
        root = Path(__file__).resolve().parents[1] / 'examples' / '0.0.3'
        for profile in ('typed', 'inferred', 'mixed'):
            with self.subTest(profile=profile):
                source = root / profile / '00 foundation' / '002 function.vq'
                status, output = execute_regression_source(source)
                self.assertEqual(status, 'PASS')
                self.assertEqual(output.strip(), '30')
