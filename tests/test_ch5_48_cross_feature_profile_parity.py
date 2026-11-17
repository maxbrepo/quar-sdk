"""Chapter 5.48: cross-feature regressions for existing function behavior."""
import unittest

from frontend.quar.errors import SemanticError
from tests.test_ch5_45_function_profile_parity import execute


class CrossFeatureProfileParityTests(unittest.TestCase):
    def test_named_arguments_with_default_parameters(self):
        base = 'int compute(int value, int multiplier = 2) { return value * multiplier; } '
        cases = {
            'typed': 'int result = compute(value = 21);',
            'inferred': 'result = compute(value = 21);',
            'mixed': 'value = 21; int result = compute(value = value);',
        }
        for profile, tail in cases.items():
            with self.subTest(profile=profile):
                self.assertEqual(execute(base + tail)['result'], 42)

    def test_recursive_function_called_through_reference(self):
        base = 'int factorial(int x) { if (x <= 1) { return 1; } return x * factorial(x - 1); } '
        cases = {
            'typed': 'function cb = &factorial; int result = (cb)(5);',
            'inferred': 'cb = &factorial; result = (cb)(5);',
            'mixed': 'cb = &factorial; int result = (cb)(5);',
        }
        for profile, tail in cases.items():
            with self.subTest(profile=profile):
                self.assertEqual(execute(base + tail)['result'], 120)

    def test_lambda_callback_with_mixed_variable_declarations(self):
        base = 'int apply(function(int)->int cb, int x) { return (cb)(x); } '
        cases = {
            'typed': 'function cb = lambda(int x)->int { return x + 1; }; int result = apply(cb, 41);',
            'inferred': 'cb = lambda(int x)->int { return x + 1; }; result = apply(cb, 41);',
            'mixed': 'cb = lambda(int x)->int { return x + 1; }; int value = 41; result = apply(cb, value);',
        }
        for profile, tail in cases.items():
            with self.subTest(profile=profile):
                self.assertEqual(execute(base + tail)['result'], 42)

    def test_incompatible_callback_with_mixed_declarations_rejected(self):
        base = ('int apply(function(int)->int cb, int x) { return (cb)(x); } '
                'string bad(int x) { return "bad"; } ')
        cases = {
            'typed': 'function cb = &bad; int result = apply(cb, 41);',
            'inferred': 'cb = &bad; result = apply(cb, 41);',
            'mixed': 'cb = &bad; int result = apply(cb, 41);',
        }
        for profile, tail in cases.items():
            with self.subTest(profile=profile):
                with self.assertRaises(SemanticError):
                    execute(base + tail)


if __name__ == '__main__':
    unittest.main()
