"""Regression tests for the conservative straight-line symbol inspector."""
import unittest
from frontend.quar import ast_nodes as ast
from qrvm.inspector_symbols import inspect_symbols
from qrvm.inspector_diagnostics import AnalysisStatus


class SymbolInspectorTests(unittest.TestCase):
    def test_declared_and_used(self):
        result = inspect_symbols([ast.VariableDeclaration('int', 'x', ast.Integer(1)), ast.ReturnStatement(ast.Variable('x'))])
        self.assertEqual(result.status, AnalysisStatus.PASS)
        self.assertFalse(result.diagnostics)

    def test_undeclared_read(self):
        result = inspect_symbols([ast.ReturnStatement(ast.Variable('missing'))])
        self.assertEqual(result.status, AnalysisStatus.FAIL)

    def test_undeclared_write(self):
        result = inspect_symbols([ast.Assignment('missing', ast.Integer(1))])
        self.assertTrue(result.has_errors)

    def test_duplicate_declaration(self):
        result = inspect_symbols([ast.VariableDeclaration('int', 'x', ast.Integer(1)), ast.VariableDeclaration('int', 'x', ast.Integer(2))])
        self.assertTrue(result.has_errors)

    def test_unused_hint(self):
        result = inspect_symbols([ast.VariableDeclaration('int', 'x', ast.Integer(1))])
        self.assertEqual(result.status, AnalysisStatus.PASS)
        self.assertEqual(result.diagnostics[0].code, 'QI-SYM-003')

    def test_unsupported_control_flow(self):
        result = inspect_symbols([ast.IfStatement(ast.Boolean(True), [], [])])
        self.assertEqual(result.status, AnalysisStatus.UNSUPPORTED)

    def test_parameter_is_known(self):
        result = inspect_symbols([ast.ReturnStatement(ast.Variable('input'))], parameters=('input',))
        self.assertEqual(result.status, AnalysisStatus.PASS)


if __name__ == '__main__':
    unittest.main()
