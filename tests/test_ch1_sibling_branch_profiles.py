"""Ensure sibling branches have independent local declarations in every profile."""
import unittest
from pathlib import Path
from main import execute_regression_source


class Chapter1SiblingBranchProfiles(unittest.TestCase):
    def test_sibling_branch_local_names(self):
        root = Path(__file__).resolve().parents[1] / 'examples' / '0.0.4'
        for profile in ('typed', 'inferred', 'mixed'):
            with self.subTest(profile=profile):
                source = root / profile / '01 primitives' / 'ch1 sibling branch scopes.vq'
                self.assertTrue(source.is_file())
                status, output = execute_regression_source(source)
                self.assertEqual((status, output.strip()), ('PASS', '1\n10'))
