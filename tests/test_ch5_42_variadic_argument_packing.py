"""Tests for the isolated variadic argument packing boundary."""
import unittest
from qrvm.variadic_arguments import pack_variadic_arguments


class VariadicPackingTests(unittest.TestCase):
    def test_zero_extra_arguments(self):
        self.assertEqual(pack_variadic_arguments(["head", "rest"], [7], 1), {"head": 7, "rest": ()})

    def test_multiple_extra_arguments(self):
        self.assertEqual(pack_variadic_arguments(["head", "rest"], [7, 8, 9], 1), {"head": 7, "rest": (8, 9)})

    def test_only_variadic_parameter(self):
        self.assertEqual(pack_variadic_arguments(["values"], [1, 2], 0), {"values": (1, 2)})

    def test_fixed_arity_unchanged(self):
        self.assertEqual(pack_variadic_arguments(["a", "b"], [1, 2]), {"a": 1, "b": 2})

    def test_missing_required_argument(self):
        with self.assertRaises(ValueError):
            pack_variadic_arguments(["head", "rest"], [], 1)

    def test_nonfinal_variadic_rejected(self):
        with self.assertRaises(ValueError):
            pack_variadic_arguments(["rest", "head"], [1, 2], 0)

    def test_duplicate_names_rejected(self):
        with self.assertRaises(ValueError):
            pack_variadic_arguments(["x", "x"], [1, 2], 1)
