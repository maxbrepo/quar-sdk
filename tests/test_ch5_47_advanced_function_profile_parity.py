"""Chapter 5.47: existing callback and lambda features across declaration profiles."""
import unittest

from frontend.quar.errors import SemanticError
from tests.test_ch5_45_function_profile_parity import execute


APPLY = 'int apply(function(int)->int cb, int x) { return (cb)(x); } '
FORWARD = 'int forward(function(int)->int cb, int x) { return apply(cb, x); } '
IDENTITY = 'int increment(int x) { return x + 1; } '


class AdvancedFunctionProfileParityTests(unittest.TestCase):
    def test_function_reference_callback_profiles(self):
        cases = {
            'typed': 'function cb = &increment; int result = apply(cb, 41);',
            'inferred': 'cb = &increment; result = apply(cb, 41);',
            'mixed': 'cb = &increment; int result = apply(cb, 41);',
        }
        for profile, tail in cases.items():
            with self.subTest(profile=profile):
                self.assertEqual(execute(IDENTITY + APPLY + tail)['result'], 42)

    def test_forwarded_callback_profiles(self):
        cases = {
            'typed': 'function cb = &increment; int result = forward(cb, 41);',
            'inferred': 'cb = &increment; result = forward(cb, 41);',
            'mixed': 'cb = &increment; int result = forward(cb, 41);',
        }
        for profile, tail in cases.items():
            with self.subTest(profile=profile):
                self.assertEqual(execute(IDENTITY + APPLY + FORWARD + tail)['result'], 42)

    def test_lambda_callback_profiles(self):
        cases = {
            'typed': 'function cb = lambda(int x)->int { return x + 1; }; int result = apply(cb, 41);',
            'inferred': 'cb = lambda(int x)->int { return x + 1; }; result = apply(cb, 41);',
            'mixed': 'cb = lambda(int x)->int { return x + 1; }; int result = apply(cb, 41);',
        }
        for profile, tail in cases.items():
            with self.subTest(profile=profile):
                self.assertEqual(execute(APPLY + tail)['result'], 42)

    def test_incompatible_callback_rejected_across_profiles(self):
        conversion = 'string convert(int x) { return "wrong"; } '
        cases = {
            'typed': 'function cb = &convert; int result = apply(cb, 41);',
            'inferred': 'cb = &convert; result = apply(cb, 41);',
            'mixed': 'cb = &convert; int result = apply(cb, 41);',
        }
        for profile, tail in cases.items():
            with self.subTest(profile=profile):
                with self.assertRaises(SemanticError):
                    execute(conversion + APPLY + tail)


if __name__ == '__main__':
    unittest.main()
