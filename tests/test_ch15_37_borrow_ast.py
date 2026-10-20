import unittest
from frontend.quar import ast_nodes as a
from qrvm.borrow_ast import analyze_borrow_ast
from qrvm.borrow_flow import BorrowFlow
from qrvm.ownership_analysis import OwnershipError


class ASTBorrowTests(unittest.TestCase):
    def test_declare_then_read(self):
        result = analyze_borrow_ast([a.VariableDeclaration('int', 'x', a.Integer(1)),
                                     a.VariableDeclaration('int', 'y', a.Variable('x'))])
        self.assertIn('y', result.analysis.at(result.graph.exit).paths[0].lifetime.declared)

    def test_assignment(self):
        analyze_borrow_ast([a.VariableDeclaration('int', 'x', a.Integer(1)),
                            a.Assignment('x', a.Integer(2))])

    def test_unknown_rhs(self):
        with self.assertRaisesRegex(OwnershipError, 'unavailable'):
            analyze_borrow_ast([a.VariableDeclaration('int', 'x', a.Variable('missing'))])

    def test_unknown_target(self):
        with self.assertRaises(OwnershipError):
            analyze_borrow_ast([a.Assignment('missing', a.Integer(1))])

    def test_branch_safe(self):
        analyze_borrow_ast([a.VariableDeclaration('int', 'x', a.Integer(1)),
                            a.IfStatement(a.Variable('x'), [a.Assignment('x', a.Integer(2))],
                                          [a.Assignment('x', a.Integer(3))])])

    def test_branch_unknown(self):
        with self.assertRaises(OwnershipError):
            analyze_borrow_ast([a.IfStatement(a.Variable('missing'), [], [])])

    def test_loop_fixpoint(self):
        result = analyze_borrow_ast([a.VariableDeclaration('int', 'x', a.Integer(1)),
                                     a.WhileStatement(a.Variable('x'), [a.Assignment('x', a.Integer(2))])])
        self.assertGreater(result.analysis.processed, 2)

    def test_unsupported_call_fails_closed(self):
        with self.assertRaisesRegex(OwnershipError, 'Unsupported'):
            analyze_borrow_ast([a.FunctionCall('print', [])])

    def test_unsupported_expression_fails_closed(self):
        with self.assertRaisesRegex(OwnershipError, 'Unsupported'):
            analyze_borrow_ast([a.VariableDeclaration('int', 'x', a.FunctionCall('f', []))])

    def test_conflicting_borrow(self):
        initial = BorrowFlow.empty().declare('x').borrow('x', 'ref')
        with self.assertRaisesRegex(OwnershipError, 'conflict'):
            analyze_borrow_ast([a.Assignment('x', a.Integer(3))], initial)

    def test_binary_reads(self):
        analyze_borrow_ast([a.VariableDeclaration('int', 'x', a.Integer(1)),
                            a.Assignment('x', a.BinaryOperation(a.Variable('x'), '+', a.Integer(1)))])

    def test_duplicate_declaration(self):
        with self.assertRaises(OwnershipError):
            analyze_borrow_ast([a.VariableDeclaration('int', 'x', a.Integer(1)),
                                a.VariableDeclaration('int', 'x', a.Integer(2))])


if __name__ == '__main__':
    unittest.main()
