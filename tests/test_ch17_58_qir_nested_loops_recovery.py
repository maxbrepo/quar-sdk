"""Executable nested-loop ownership and SSA regression coverage."""
import unittest

from frontend.quar.ast_nodes import (Assignment, BinaryOperation, BreakStatement,
    ContinueStatement, ForStatement, FunctionDefinition, FunctionParameter,
    IfStatement, Integer, ReturnStatement, Variable, VariableDeclaration,
    WhileStatement)
from test_ch17_52_qir_for_recovery import ForRecoveryTests


def var(name):
    return Variable(name)


def op(left, operator, right):
    return BinaryOperation(left, operator, right)


class NestedLoopRecoveryTests(unittest.TestCase):
    execute_both = ForRecoveryTests.execute_both

    def function(self, outer_body):
        return FunctionDefinition('i32', 'for_counter',
            [FunctionParameter('i32', 'limit')], [
                VariableDeclaration('i32', 'outer', Integer(0)),
                VariableDeclaration('i32', 'inner', Integer(0)),
                VariableDeclaration('i32', 'total', Integer(0)),
                ForStatement('outer', Integer(0), op(var('outer'), '<', var('limit')), outer_body),
                ReturnStatement(var('total'))])

    def test_nested_for_continue_advances_inner_counter(self):
        function = self.function([
            ForStatement('inner', Integer(0), op(var('inner'), '<', Integer(4)), [
                IfStatement(op(var('inner'), '==', Integer(1)), [ContinueStatement()], []),
                Assignment('total', op(var('total'), '+', Integer(1))),
            ]),
        ])
        self.execute_both(function, [(0, 0), (1, 3), (3, 9)])

    def test_inner_break_does_not_break_outer(self):
        function = self.function([
            ForStatement('inner', Integer(0), op(var('inner'), '<', Integer(5)), [
                IfStatement(op(var('inner'), '==', Integer(2)), [BreakStatement()], []),
                Assignment('total', op(var('total'), '+', Integer(1))),
            ]),
        ])
        self.execute_both(function, [(0, 0), (1, 2), (4, 8)])

    def test_inner_while_updates_outer_accumulator(self):
        function = self.function([
            Assignment('inner', Integer(0)),
            WhileStatement(op(var('inner'), '<', Integer(2)), [
                Assignment('total', op(var('total'), '+', Integer(1))),
                Assignment('inner', op(var('inner'), '+', Integer(1))),
            ]),
        ])
        self.execute_both(function, [(0, 0), (1, 2), (4, 8)])


if __name__ == '__main__':
    unittest.main()
