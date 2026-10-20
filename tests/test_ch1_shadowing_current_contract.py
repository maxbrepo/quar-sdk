"""Document current shadowing limitations before implementing lexical bindings."""
import unittest
from pathlib import Path
from main import execute_regression_source


class ShadowingCurrentContract(unittest.TestCase):
    def test_explicit_redeclaration_is_rejected(self):
        root = Path(__file__).parent / 'fixtures' / 'ch1_shadowing'
        for profile in ('typed', 'mixed'):
            with self.subTest(profile=profile):
                status, message = execute_regression_source(root / profile / 'shadowing_rejected.vq')
                self.assertEqual(status, 'FAIL')
                self.assertIn("Variable 'value' is already declared", message)

    def test_inferred_assignment_does_not_create_shadow_binding(self):
        root = Path(__file__).parent / 'fixtures' / 'ch1_shadowing'
        status, output = execute_regression_source(root / 'inferred' / 'shadowing_rejected.vq')
        self.assertEqual(status, 'PASS', output)
        self.assertEqual(output.strip(), '20\n20')
