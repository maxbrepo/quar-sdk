"""Tests for the independent Quar Inspector diagnostic contract."""
import unittest

from qrvm.inspector_diagnostics import (
    AnalysisStatus, Diagnostic, InspectionResult, Severity, SourceLocation,
)


class InspectorDiagnosticsTests(unittest.TestCase):
    def test_location(self):
        self.assertEqual(SourceLocation("main.vq", 3, 2).line, 3)

    def test_invalid_location(self):
        with self.assertRaises(ValueError):
            SourceLocation("main.vq", 0, 1)

    def test_diagnostic_fields(self):
        finding = Diagnostic("QV001", Severity.WARNING, "Unused value", "symbols")
        self.assertEqual(finding.code, "QV001")

    def test_missing_code(self):
        with self.assertRaises(ValueError):
            Diagnostic("", Severity.ERROR, "Failure", "types")

    def test_empty_result(self):
        self.assertFalse(InspectionResult(AnalysisStatus.PASS).has_errors)

    def test_error_result(self):
        finding = Diagnostic("QV002", Severity.ERROR, "Missing name", "symbols")
        self.assertTrue(InspectionResult(AnalysisStatus.FAIL, (finding,)).has_errors)

    def test_pass_rejects_error(self):
        finding = Diagnostic("QV002", Severity.ERROR, "Missing name", "symbols")
        with self.assertRaises(ValueError):
            InspectionResult(AnalysisStatus.PASS, (finding,))

    def test_unknown_is_not_pass(self):
        self.assertNotEqual(AnalysisStatus.UNKNOWN, AnalysisStatus.PASS)

    def test_unsupported_is_not_pass(self):
        self.assertNotEqual(AnalysisStatus.UNSUPPORTED, AnalysisStatus.PASS)


if __name__ == "__main__":
    unittest.main()
