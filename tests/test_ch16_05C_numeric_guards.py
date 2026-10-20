"""Regression checks for numeric literal evidence and source ranges."""
import unittest
from qrvm.inspector_diagnostics import AnalysisStatus
from qrvm.inspector_numeric import inspect_numeric_conversion


class NumericGuardTests(unittest.TestCase):
    def test_literal_outside_source_range(self):
        result = inspect_numeric_conversion("i8", "i16", literal=200)
        self.assertEqual(result.status, AnalysisStatus.FAIL)
        self.assertEqual(result.diagnostics[0].code, "QI-NUM-005")

    def test_negative_unsigned_source(self):
        self.assertEqual(inspect_numeric_conversion("u8", "i16", literal=-1).status, AnalysisStatus.FAIL)

    def test_float_to_int_literal_hint_is_not_proof(self):
        self.assertEqual(inspect_numeric_conversion("f64", "i8", literal=2).status, AnalysisStatus.UNKNOWN)

    def test_valid_integer_literal_narrowing(self):
        self.assertEqual(inspect_numeric_conversion("i32", "i8", literal=42).status, AnalysisStatus.PASS)

    def test_invalid_literal_type(self):
        with self.assertRaises(TypeError):
            inspect_numeric_conversion("i32", "i8", literal=1.5)


if __name__ == "__main__":
    unittest.main()
