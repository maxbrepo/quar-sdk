"""Executable checks for explicit infinite loops with owned exit transfers."""
import unittest

from frontend.quar.ast_nodes import (Assignment, BinaryOperation, BreakStatement,
    ContinueStatement, ForStatement, FunctionDefinition, FunctionParameter,
    IfStatement, Integer, LoopStatement, ReturnStatement, Variable,
    VariableDeclaration)
from test_ch17_52_qir_for_recovery import ForRecoveryTests


def v(name):
    return Variable(name)


def op(left, operator, right):
    return BinaryOperation(left, operator, right)


class ExplicitLoopRecoveryTests(unittest.TestCase):
    execute_both = ForRecoveryTests.execute_both

    def make_function(self, body):
        return FunctionDefinition('i32', 'for_counter',
            [FunctionParameter('i32', 'limit')], [
                VariableDeclaration('i32', 'counter', Integer(0)),
                VariableDeclaration('i32', 'total', Integer(0)),
                LoopStatement(body), ReturnStatement(v('total'))])

    def test_conditional_break_and_zero_iterations(self):
        self.execute_both(self.make_function([
            IfStatement(op(v('counter'), '>=', v('limit')), [BreakStatement()], []),
            Assignment('total', op(v('total'), '+', Integer(2))),
            Assignment('counter', op(v('counter'), '+', Integer(1))),
        ]), [(0, 0), (1, 2), (4, 8)])

    def test_conditional_continue(self):
        self.execute_both(self.make_function([
            Assignment('counter', op(v('counter'), '+', Integer(1))),
            IfStatement(op(v('counter'), '>', v('limit')), [BreakStatement()], []),
            IfStatement(op(v('counter'), '==', Integer(2)), [ContinueStatement()], []),
            Assignment('total', op(v('total'), '+', Integer(1))),
        ]), [(0, 0), (1, 1), (4, 3)])

    def test_nested_loop_break_ownership(self):
        self.execute_both(self.make_function([
            Assignment('counter', op(v('counter'), '+', Integer(1))),
            IfStatement(op(v('counter'), '>', v('limit')), [BreakStatement()], []),
            LoopStatement([
                Assignment('total', op(v('total'), '+', Integer(1))),
                BreakStatement(),
            ]),
        ]), [(0, 0), (1, 1), (3, 3)])


if __name__ == '__main__':
    unittest.main()
