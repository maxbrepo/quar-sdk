"""Cycle A numeric-type contract tests; no runtime implementation changes."""
import unittest

from frontend.quar.numeric_types import (
    FLOAT_BITS,
    INTEGER_BITS,
    canonical_numeric_type,
    integer_conversion_is_safe,
    integer_range,
    is_numeric_type,
)
from frontend.quar.qir.types import canonical_type, is_integer, is_numeric


class TypedNumericContractA01(unittest.TestCase):
    def test_all_fixed_width_integer_ranges(self):
        for width in (8, 16, 32, 64, 128):
            with self.subTest(width=width, signed=True):
                self.assertEqual(integer_range(f"i{width}"),
                                 (-(1 << (width - 1)), (1 << (width - 1)) - 1))
            with self.subTest(width=width, signed=False):
                self.assertEqual(integer_range(f"u{width}"), (0, (1 << width) - 1))

    def test_numeric_frontend_and_qir_type_registry_overlap(self):
        for name in (*INTEGER_BITS, *FLOAT_BITS):
            with self.subTest(type=name):
                self.assertTrue(is_numeric_type(name))
                if name == "long_double":
                    continue  # ABI and QIR availability must be audited separately.
                self.assertTrue(is_numeric(canonical_type(name)))
                self.assertEqual(is_integer(canonical_type(name)), name in INTEGER_BITS)

    def test_aliases_are_frontend_only(self):
        self.assertEqual(canonical_numeric_type("byte"), "u8")
        self.assertEqual(canonical_numeric_type("int"), "i32")
        with self.assertRaises(ValueError):
            canonical_type("int")

    def test_widening_is_range_based(self):
        self.assertTrue(integer_conversion_is_safe("u8", "i16"))
        self.assertTrue(integer_conversion_is_safe("i16", "i32"))
        self.assertFalse(integer_conversion_is_safe("i16", "u16"))
        self.assertFalse(integer_conversion_is_safe("u64", "i64"))
        self.assertFalse(integer_conversion_is_safe("f32", "i64"))


if __name__ == "__main__":
    unittest.main()
