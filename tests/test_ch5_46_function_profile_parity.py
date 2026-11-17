"""Chapter 5.46: parity tests for existing defaults, named arguments and recursion."""
import unittest
from tests.test_ch5_45_function_profile_parity import execute


class FunctionArgumentProfileParityTests(unittest.TestCase):
    def test_default_parameter_profiles(self):
        function = 'int scale(int value, int factor = 2) { return value * factor; } '
        for profile, tail in {
            'typed': 'int result = scale(21);',
            'inferred': 'result = scale(21);',
            'mixed': 'value = 21; int result = scale(value);',
        }.items():
            with self.subTest(profile=profile):
                self.assertEqual(execute(function + tail)['result'], 42)

    def test_explicit_default_override_profiles(self):
        function = 'int scale(int value, int factor = 2) { return value * factor; } '
        for profile, tail in {
            'typed': 'int result = scale(14, 3);',
            'inferred': 'result = scale(14, 3);',
            'mixed': 'factor = 3; int result = scale(14, factor);',
        }.items():
            with self.subTest(profile=profile):
                self.assertEqual(execute(function + tail)['result'], 42)

    def test_named_arguments_profiles(self):
        function = 'int subtract(int left, int right) { return left - right; } '
        for profile, tail in {
            'typed': 'int result = subtract(right = 3, left = 45);',
            'inferred': 'result = subtract(right = 3, left = 45);',
            'mixed': 'right = 3; int result = subtract(right = right, left = 45);',
        }.items():
            with self.subTest(profile=profile):
                self.assertEqual(execute(function + tail)['result'], 42)

    def test_recursion_profiles(self):
        function = 'int factorial(int x) { if (x <= 1) { return 1; } return x * factorial(x - 1); } '
        for profile, tail in {
            'typed': 'int result = factorial(5);',
            'inferred': 'result = factorial(5);',
            'mixed': 'value = 5; int result = factorial(value);',
        }.items():
            with self.subTest(profile=profile):
                self.assertEqual(execute(function + tail)['result'], 120)


if __name__ == '__main__':
    unittest.main()
