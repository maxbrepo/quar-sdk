"""AST numeric inspection regression tests."""
import unittest
from frontend.quar import ast_nodes as ast
from qrvm.inspector_diagnostics import AnalysisStatus
from qrvm.inspector_numeric_ast import inspect_numeric_statements


class NumericAstTests(unittest.TestCase):
    def test_literal_fits(self):
        result = inspect_numeric_statements([ast.VariableDeclaration('i8', 'x', ast.Integer(127))])
        self.assertEqual(result.status, AnalysisStatus.PASS)

    def test_literal_overflow(self):
        result = inspect_numeric_statements([ast.VariableDeclaration('i8', 'x', ast.Integer(128))])
        self.assertEqual(result.status, AnalysisStatus.FAIL)
        self.assertEqual(result.diagnostics[0].code, 'QI-NUM-001')

    def test_unsigned_negative(self):
        result = inspect_numeric_statements([ast.VariableDeclaration('u8', 'x', ast.Integer(-1))])
        self.assertEqual(result.status, AnalysisStatus.FAIL)

    def test_assignment_overflow(self):
        result = inspect_numeric_statements([ast.VariableDeclaration('u8', 'x', None), ast.Assignment('x', ast.Integer(256))])
        self.assertEqual(result.status, AnalysisStatus.FAIL)

    def test_variable_narrowing(self):
        result = inspect_numeric_statements([ast.VariableDeclaration('i64', 'a', None), ast.VariableDeclaration('i8', 'b', ast.Variable('a'))])
        self.assertEqual(result.status, AnalysisStatus.UNKNOWN)
        self.assertEqual(result.diagnostics[0].code, 'QI-NUM-002')

    def test_safe_widening(self):
        result = inspect_numeric_statements([ast.VariableDeclaration('u8', 'a', None), ast.VariableDeclaration('i16', 'b', ast.Variable('a'))])
        self.assertEqual(result.status, AnalysisStatus.PASS)

    def test_unsupported_expression(self):
        result = inspect_numeric_statements([ast.VariableDeclaration('i8', 'x', ast.BinaryOperation(ast.Integer(1), '+', ast.Integer(2)))])
        self.assertEqual(result.status, AnalysisStatus.UNSUPPORTED)

    def test_float_literal_inconclusive(self):
        result = inspect_numeric_statements([ast.VariableDeclaration('f32', 'x', ast.Integer(123))])
        self.assertEqual(result.status, AnalysisStatus.UNKNOWN)

    def test_undeclared_source(self):
        result = inspect_numeric_statements([ast.VariableDeclaration('i8', 'x', ast.Variable('missing'))])
        self.assertEqual(result.status, AnalysisStatus.UNSUPPORTED)


if __name__ == '__main__':
    unittest.main()
