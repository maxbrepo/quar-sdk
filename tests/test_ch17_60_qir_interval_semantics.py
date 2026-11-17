"""Executable interval-boundary regression for canonical counter loops."""
import unittest

from frontend.quar.ast_nodes import (Assignment, BinaryOperation, ForStatement,
    FunctionDefinition, FunctionParameter, Integer, ReturnStatement, Variable,
    VariableDeclaration)
import test_ch17_52_qir_for_recovery as for_helpers


class IntervalSemanticsTests(unittest.TestCase):
    execute_both = for_helpers.ForRecoveryTests.execute_both

    def function(self, start, operator, step, direction=0):
        counter = Variable('counter')
        return FunctionDefinition('i32', 'for_counter',
            [FunctionParameter('i32', 'limit')], [
                VariableDeclaration('i32', 'counter', Integer(0)),
                VariableDeclaration('i32', 'total', Integer(0)),
                ForStatement('counter', Integer(start),
                    BinaryOperation(counter, operator, Variable('limit')),
                    [Assignment('total', BinaryOperation(Variable('total'), '+', counter))],
                    step, direction),
                ReturnStatement(Variable('total'))])

    def test_exclusive_ascending_interval(self):
        self.execute_both(self.function(1, '<', 2), [(1, 0), (2, 1), (6, 9), (7, 9)])

    def test_inclusive_ascending_interval(self):
        self.execute_both(self.function(1, '<=', 2), [(0, 0), (1, 1), (5, 9), (6, 9)])

    def test_exclusive_descending_interval(self):
        self.execute_both(self.function(7, '>', 2, -1), [(7, 0), (6, 7), (0, 16), (-1, 16)])

    def test_inclusive_descending_interval(self):
        self.execute_both(self.function(7, '>=', 3, -1), [(8, 0), (7, 7), (1, 12), (0, 12)])

    def test_nonzero_start_and_exact_boundary(self):
        self.execute_both(self.function(4, '<', 3), [(4, 0), (5, 4), (10, 11)])


if __name__ == '__main__':
    unittest.main()
