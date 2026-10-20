"""Regression checks for conservative numeric conversion inspection."""
import unittest
from qrvm.inspector_diagnostics import AnalysisStatus
from qrvm.inspector_numeric import inspect_numeric_conversion


class NumericInspectionTests(unittest.TestCase):
    def test_alias_identity(self):
        self.assertEqual(inspect_numeric_conversion('int', 'i32').status, AnalysisStatus.PASS)

    def test_safe_widening(self):
        self.assertEqual(inspect_numeric_conversion('u8', 'i16').status, AnalysisStatus.PASS)

    def test_unsigned_to_signed_narrowing(self):
        self.assertEqual(inspect_numeric_conversion('u16', 'i16').status, AnalysisStatus.UNKNOWN)

    def test_negative_to_unsigned(self):
        self.assertEqual(inspect_numeric_conversion('i16', 'u16', literal=-1).status, AnalysisStatus.FAIL)

    def test_constant_overflow(self):
        result = inspect_numeric_conversion('i32', 'i8', literal=128)
        self.assertEqual(result.diagnostics[0].code, 'QI-NUM-001')

    def test_fitting_constant(self):
        self.assertEqual(inspect_numeric_conversion('i32', 'i8', literal=127).status, AnalysisStatus.PASS)

    def test_float_to_integer(self):
        self.assertEqual(inspect_numeric_conversion('f64', 'i32').status, AnalysisStatus.UNKNOWN)

    def test_integer_to_float(self):
        self.assertEqual(inspect_numeric_conversion('i64', 'f32').status, AnalysisStatus.UNKNOWN)

    def test_unsupported_type(self):
        self.assertEqual(inspect_numeric_conversion('string', 'i32').status, AnalysisStatus.UNSUPPORTED)


if __name__ == '__main__':
    unittest.main()
