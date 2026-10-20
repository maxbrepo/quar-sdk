"""Regression tests for conservative source attribution in Scope Inspector."""
import unittest
from frontend.quar import ast_nodes as ast
from qrvm.inspector import inspect_program
from qrvm.inspector_scopes import inspect_scopes


class DiagnosticLocationsTests(unittest.TestCase):
    def test_undeclared_read_uses_expression_span(self):
        variable = ast.Variable('missing')
        variable.start, variable.end = (3, 10), (3, 17)
        result = inspect_scopes([ast.ReturnStatement(variable)], path='demo.vq')
        finding = next(d for d in result.diagnostics if d.code == 'QI-SYM-001')
        self.assertEqual((finding.location.line, finding.location.column), (3, 10))
        self.assertEqual((finding.source_range.end.line, finding.source_range.end.column), (3, 17))

    def test_duplicate_declaration_uses_second_declaration(self):
        first = ast.VariableDeclaration('int', 'x', ast.Integer(1))
        second = ast.VariableDeclaration('int', 'x', ast.Integer(2))
        second.start, second.end = (4, 2), (4, 12)
        result = inspect_scopes([first, second], path='demo.vq')
        finding = next(d for d in result.diagnostics if d.code == 'QI-SYM-002')
        self.assertEqual(finding.location.line, 4)

    def test_missing_position_remains_missing(self):
        result = inspect_scopes([ast.ReturnStatement(ast.Variable('missing'))], path='demo.vq')
        self.assertIsNone(result.diagnostics[0].location)

    def test_path_is_optional_for_backward_compatibility(self):
        variable = ast.Variable('missing')
        variable.start, variable.end = (2, 1), (2, 8)
        result = inspect_scopes([ast.ReturnStatement(variable)])
        self.assertIsNone(result.diagnostics[0].location)

    def test_coordinator_passes_source_path(self):
        variable = ast.Variable('missing')
        variable.start, variable.end = (7, 5), (7, 12)
        report = inspect_program([ast.ReturnStatement(variable)], enabled=('scopes',), path='demo.vq')
        self.assertEqual(report.result.diagnostics[0].location.line, 7)


if __name__ == '__main__':
    unittest.main()
