"""Regression tests for optional half-open source ranges."""
import unittest
from qrvm.inspector_diagnostics import Diagnostic, Severity, SourceLocation, SourceRange
from qrvm.inspector_format import diagnostic_record, format_diagnostic


class SourceRangeTests(unittest.TestCase):
    def test_single_line_range(self):
        span = SourceRange(SourceLocation("a.vq", 2, 3), SourceLocation("a.vq", 2, 8))
        item = Diagnostic("QI-TST-009", Severity.ERROR, "invalid", "test", source_range=span)
        self.assertIn("a.vq:2:3-2:8", format_diagnostic(item))
        self.assertEqual(diagnostic_record(item)["range"]["end"]["column"], 8)
        self.assertEqual(diagnostic_record(item)["location"]["column"], 3)

    def test_multiline_range(self):
        span = SourceRange(SourceLocation("a.vq", 2, 12), SourceLocation("a.vq", 4, 1))
        self.assertEqual(span.end.line, 4)

    def test_rejects_reverse_and_empty_ranges(self):
        with self.assertRaises(ValueError):
            SourceRange(SourceLocation("a", 2, 4), SourceLocation("a", 2, 4))
        with self.assertRaises(ValueError):
            SourceRange(SourceLocation("a", 3, 1), SourceLocation("a", 2, 10))

    def test_rejects_cross_file_ranges(self):
        with self.assertRaises(ValueError):
            SourceRange(SourceLocation("a", 1, 1), SourceLocation("b", 1, 2))

    def test_rejects_mismatched_legacy_location(self):
        span = SourceRange(SourceLocation("a", 1, 1), SourceLocation("a", 1, 2))
        with self.assertRaises(ValueError):
            Diagnostic("QI-TST-009", Severity.ERROR, "invalid", "test",
                       location=SourceLocation("a", 1, 2), source_range=span)

    def test_legacy_diagnostics_still_work(self):
        item = Diagnostic("QI-TST-009", Severity.INFO, "legacy", "test",
                          SourceLocation("a", 1, 2))
        self.assertIsNone(diagnostic_record(item)["range"])
        self.assertEqual(diagnostic_record(item)["location"]["column"], 2)


if __name__ == "__main__":
    unittest.main()
