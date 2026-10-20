"""Validate nested lexical scope examples across all declaration profiles."""
import unittest
from pathlib import Path
from main import execute_regression_source


class Chapter1ScopeProfileExamples(unittest.TestCase):
    def test_nested_scope_isolation_all_profiles(self):
        root = Path(__file__).resolve().parents[1] / 'examples' / '0.0.4'
        for profile in ('typed', 'inferred', 'mixed'):
            with self.subTest(profile=profile):
                source = root / profile / '01 primitives' / 'ch1 nested scope isolation.vq'
                self.assertTrue(source.is_file())
                status, output = execute_regression_source(source)
                self.assertEqual(status, 'PASS', output)
                self.assertEqual(output.strip(), '15\n10')
