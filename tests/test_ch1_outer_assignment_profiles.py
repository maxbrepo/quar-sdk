"""Keep assignment-to-visible-binding semantics stable across profiles."""
import unittest
from pathlib import Path
from main import execute_regression_source


class Chapter1OuterAssignmentProfiles(unittest.TestCase):
    def test_assignment_targets_existing_outer_binding(self):
        root = Path(__file__).resolve().parents[1] / "examples" / "0.0.4"
        for profile in ("typed", "inferred", "mixed"):
            with self.subTest(profile=profile):
                source = root / profile / "01 primitives" / "ch1 outer assignment across scopes.vq"
                status, output = execute_regression_source(source)
                self.assertEqual(status, "PASS", output)
                self.assertEqual(output.strip(), "20\n30")
