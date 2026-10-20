"""Static bounds regression tests."""
import unittest
from frontend.quar import ast_nodes as ast
from qrvm.inspector_bounds import inspect_array_bounds
from qrvm.inspector_diagnostics import AnalysisStatus


class BoundsTests(unittest.TestCase):
    def check(self, statements, expected):
        self.assertEqual(inspect_array_bounds(statements).status, expected)

    def test_valid(self):
        self.check([ast.ArrayDeclaration('i32', 'a', 3), ast.ArrayAccess('a', ast.Integer(2))], AnalysisStatus.PASS)

    def test_equal_length(self):
        self.check([ast.ArrayDeclaration('i32', 'a', 3), ast.ArrayAccess('a', ast.Integer(3))], AnalysisStatus.FAIL)

    def test_negative(self):
        self.check([ast.ArrayDeclaration('i32', 'a', 3), ast.ArrayAccess('a', ast.Integer(-1))], AnalysisStatus.FAIL)

    def test_arithmetic(self):
        self.check([ast.ArrayDeclaration('i32', 'a', 3), ast.ArrayAccess('a', ast.BinaryOperation(ast.Integer(1), '+', ast.Integer(2)))], AnalysisStatus.FAIL)

    def test_dynamic(self):
        self.check([ast.ArrayDeclaration('i32', 'a', 3), ast.ArrayAccess('a', ast.Variable('i'))], AnalysisStatus.UNKNOWN)

    def test_unknown_size(self):
        self.check([ast.ArrayDeclaration('i32', 'a', None), ast.ArrayAccess('a', ast.Integer(1))], AnalysisStatus.UNKNOWN)

    def test_second_dimension(self):
        self.check([ast.ArrayDeclaration('i32', 'a', 2, second_size=3), ast.ArrayAccess('a', ast.Integer(1), ast.Integer(3))], AnalysisStatus.FAIL)

    def test_assignment(self):
        self.check([ast.ArrayDeclaration('i32', 'a', 2), ast.ArrayAssignment('a', ast.Integer(2), ast.Integer(5))], AnalysisStatus.FAIL)

    def test_undeclared(self):
        self.check([ast.ArrayAccess('missing', ast.Integer(0))], AnalysisStatus.UNSUPPORTED)


if __name__ == '__main__':
    unittest.main()
