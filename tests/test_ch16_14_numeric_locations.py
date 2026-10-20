"""Chapter 16.14: numeric findings retain precise optional AST spans."""
import unittest
from frontend.quar import ast_nodes as ast
from qrvm.inspector import inspect_program
from qrvm.inspector_numeric_ast import inspect_numeric_statements


class NumericLocationTests(unittest.TestCase):
    def test_literal_overflow_points_to_literal(self):
        literal = ast.Integer(128)
        literal.start, literal.end = (3, 12), (3, 15)
        result = inspect_numeric_statements([ast.VariableDeclaration('i8', 'x', literal)], path='example.vq')
        finding = result.diagnostics[0]
        self.assertEqual(finding.code, 'QI-NUM-001')
        self.assertEqual((finding.location.line, finding.location.column), (3, 12))
        self.assertEqual(finding.source_range.end.column, 15)

    def test_narrowing_points_to_source_variable(self):
        source = ast.Variable('wide')
        source.start, source.end = (7, 11), (7, 15)
        result = inspect_numeric_statements([
            ast.VariableDeclaration('i64', 'wide', None),
            ast.VariableDeclaration('i8', 'small', source),
        ], path='example.vq')
        self.assertEqual(result.diagnostics[0].code, 'QI-NUM-002')
        self.assertEqual(result.diagnostics[0].location.column, 11)

    def test_assignment_uses_rhs_not_statement(self):
        literal = ast.Integer(300)
        literal.start, literal.end = (5, 8), (5, 11)
        statement = ast.Assignment('x', literal)
        statement.start, statement.end = (5, 1), (5, 12)
        result = inspect_numeric_statements([
            ast.VariableDeclaration('u8', 'x', None), statement,
        ], path='example.vq')
        self.assertEqual(result.diagnostics[0].location.column, 8)

    def test_no_path_preserves_unlocated_diagnostic(self):
        literal = ast.Integer(300)
        literal.start, literal.end = (2, 3), (2, 6)
        result = inspect_numeric_statements([ast.VariableDeclaration('u8', 'x', literal)])
        self.assertIsNone(result.diagnostics[0].location)

    def test_missing_ast_coordinates_remain_unknown(self):
        result = inspect_numeric_statements([
            ast.VariableDeclaration('i8', 'x', ast.Integer(200)),
        ], path='example.vq')
        self.assertIsNone(result.diagnostics[0].location)

    def test_coordinator_forwards_path(self):
        literal = ast.Integer(500)
        literal.start, literal.end = (9, 4), (9, 7)
        report = inspect_program([ast.VariableDeclaration('u8', 'x', literal)],
                                 enabled=('numeric',), path='example.vq')
        self.assertEqual(report.result.diagnostics[0].location.line, 9)


if __name__ == '__main__':
    unittest.main()
