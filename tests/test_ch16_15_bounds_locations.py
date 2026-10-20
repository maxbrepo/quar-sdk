"""Regression tests for Chapter 16.15 bounds source locations."""
import unittest
from frontend.quar import ast_nodes as ast
from qrvm.inspector_bounds import inspect_array_bounds
from qrvm.inspector import inspect_program
from qrvm.inspector_diagnostics import AnalysisStatus


class BoundsLocationsTests(unittest.TestCase):
    def make_access(self, index, second=None):
        return [ast.ArrayDeclaration('i32', 'values', 2, second_size=(3 if second is not None else None)),
                ast.ArrayAccess('values', index, second)]

    def test_index_span(self):
        index = ast.Integer(3)
        index.start, index.end = (4, 10), (4, 11)
        finding = inspect_array_bounds(self.make_access(index), path='demo.qr').diagnostics[0]
        self.assertEqual((finding.location.line, finding.location.column), (4, 10))
        self.assertEqual(finding.source_range.end.column, 11)

    def test_no_path_remains_compatible(self):
        index = ast.Integer(3)
        index.start, index.end = (4, 10), (4, 11)
        finding = inspect_array_bounds(self.make_access(index)).diagnostics[0]
        self.assertIsNone(finding.location)

    def test_missing_coordinates_are_not_fabricated(self):
        finding = inspect_array_bounds(self.make_access(ast.Integer(3)), path='demo.qr').diagnostics[0]
        self.assertIsNone(finding.location)

    def test_second_dimension_location(self):
        first, second = ast.Integer(1), ast.Integer(4)
        first.start, first.end = (7, 2), (7, 3)
        second.start, second.end = (7, 5), (7, 6)
        finding = inspect_array_bounds(self.make_access(first, second), path='demo.qr').diagnostics[0]
        self.assertEqual(finding.location.column, 5)
        self.assertIn('dimension 2', finding.message)

    def test_coordinator_forwards_path(self):
        index = ast.Integer(4)
        index.start, index.end = (9, 4), (9, 5)
        report = inspect_program(self.make_access(index), enabled=('bounds',), path='demo.qr')
        self.assertEqual(report.result.status, AnalysisStatus.FAIL)
        self.assertEqual(report.result.diagnostics[0].location.line, 9)

    def test_unknown_index_does_not_claim_safety(self):
        result = inspect_array_bounds(self.make_access(ast.Variable('i')), path='demo.qr')
        self.assertEqual(result.status, AnalysisStatus.UNKNOWN)
        self.assertFalse(result.diagnostics)


if __name__ == '__main__':
    unittest.main()
