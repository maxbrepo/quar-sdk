"""Regression tests for the conservative Inspector AST location bridge."""
import unittest
from types import SimpleNamespace

from qrvm.inspector_ast_locations import (
    attach_node_location, node_source_location, node_source_range,
)
from qrvm.inspector_diagnostics import Diagnostic, Severity, SourceLocation, SourceRange


class AstLocationTests(unittest.TestCase):
    def setUp(self):
        self.finding = Diagnostic('QI-TEST-001', Severity.WARNING, 'example', 'test')

    def test_unannotated_ast_remains_unknown(self):
        self.assertIsNone(node_source_location(SimpleNamespace(name='x'), 'sample.vq'))
        self.assertEqual(attach_node_location(self.finding, SimpleNamespace(), 'sample.vq'), self.finding)

    def test_explicit_start_end_coordinates(self):
        node = SimpleNamespace(start=(2, 3), end=(2, 8))
        result = attach_node_location(self.finding, node, 'sample.vq')
        self.assertEqual(result.source_range.end.column, 8)
        self.assertEqual(result.location, SourceLocation('sample.vq', 2, 3))

    def test_multiline_span(self):
        node = SimpleNamespace(start=(2, 3), end=(4, 1))
        self.assertEqual(node_source_range(node, 'a.vq').end.line, 4)

    def test_line_column_fallback(self):
        node = SimpleNamespace(line=5, column=7)
        self.assertEqual(node_source_location(node, 'a.vq'), SourceLocation('a.vq', 5, 7))

    def test_invalid_span_does_not_guess(self):
        self.assertIsNone(node_source_range(SimpleNamespace(start=(4, 2), end=(3, 1)), 'a.vq'))

    def test_bool_is_not_valid_coordinate(self):
        self.assertIsNone(node_source_range(SimpleNamespace(start=(True, 1), end=(2, 1)), 'a.vq'))

    def test_existing_diagnostic_location_is_preserved(self):
        existing = Diagnostic('QI-TEST-001', Severity.WARNING, 'example', 'test',
                              location=SourceLocation('old.vq', 1, 1))
        node = SimpleNamespace(start=(2, 1), end=(2, 5))
        self.assertEqual(attach_node_location(existing, node, 'new.vq'), existing)

    def test_explicit_range_path_must_match(self):
        span = SourceRange(SourceLocation('old.vq', 1, 1), SourceLocation('old.vq', 1, 2))
        self.assertIsNone(node_source_range(SimpleNamespace(source_range=span), 'new.vq'))


if __name__ == '__main__':
    unittest.main()
