"""Regression tests for the isolated variadic argument boundary."""
import unittest

from qrvm.variadic_arguments import pack_variadic_arguments


class VariadicBoundaryRegressionTests(unittest.TestCase):
    def test_fixed_arity_rejects_duplicate_parameter_names(self):
        with self.assertRaisesRegex(ValueError, "Duplicate parameter names"):
            pack_variadic_arguments(["x", "x"], [1, 2])

    def test_empty_variadic_tail_is_tuple(self):
        self.assertEqual(pack_variadic_arguments(["x", "rest"], [1], 1), {"x": 1, "rest": ()})

    def test_only_variadic_parameter_accepts_no_arguments(self):
        self.assertEqual(pack_variadic_arguments(["rest"], [], 0), {"rest": ()})

    def test_invalid_variadic_index_rejected(self):
        for index in (True, -1, 2, "1"):
            with self.subTest(index=index), self.assertRaises(ValueError):
                pack_variadic_arguments(["x", "rest"], [1, 2], index)


if __name__ == "__main__":
    unittest.main()
