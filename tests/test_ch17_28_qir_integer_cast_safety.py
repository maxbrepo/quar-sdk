"""Classification tests for explicit QIR integer conversions."""
import unittest

from frontend.quar.qir.cast_safety import assess_integer_cast, integer_range
from frontend.quar.qir.model import QType


class IntegerCastSafetyTests(unittest.TestCase):
    def test_signed_widening(self):
        assessment = assess_integer_cast(QType("i8"), QType("i32"))
        self.assertFalse(assessment.requires_runtime_check)

    def test_unsigned_widening(self):
        self.assertFalse(assess_integer_cast(QType("u8"), QType("i16")).requires_runtime_check)

    def test_narrowing_requires_check(self):
        self.assertTrue(assess_integer_cast(QType("i64"), QType("i32")).requires_runtime_check)
        self.assertTrue(assess_integer_cast(QType("u16"), QType("u8")).requires_runtime_check)

    def test_signedness_requires_check_when_range_not_contained(self):
        self.assertTrue(assess_integer_cast(QType("i8"), QType("u8")).requires_runtime_check)
        self.assertTrue(assess_integer_cast(QType("u8"), QType("i8")).requires_runtime_check)

    def test_exact_ranges(self):
        self.assertEqual(integer_range(QType("i8")), (-128, 127))
        self.assertEqual(integer_range(QType("u8")), (0, 255))
        self.assertEqual(integer_range(QType("i128")), (-(1 << 127), (1 << 127) - 1))

    def test_non_integer_rejected(self):
        for name in ("bool", "f32", "void", "invalid"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                integer_range(QType(name))


if __name__ == "__main__":
    unittest.main()
