"""Regression cases for nested loop transfers and function returns."""
import unittest

from frontend.quar.ast_nodes import (
    Assignment, BinaryOperation, BreakStatement, ContinueStatement, ForStatement,
    IfStatement, Integer, ReturnStatement, Variable, VariableDeclaration, WhileStatement,
)
from test_ch17_66_qir_array_source_integration import SourceArrayIntegrationTests


def ref(name):
    return Variable(name)


def op(left, operator, right):
    return BinaryOperation(left, operator, right)


class NestedTransferReconciliationTests(unittest.TestCase):
    run_both = SourceArrayIntegrationTests.run_both

    def test_inner_break_does_not_break_outer_loop(self):
        self.run_both([
            VariableDeclaration('i32', 'i', Integer(0)),
            VariableDeclaration('i32', 'j', Integer(0)),
            VariableDeclaration('i32', 'count', Integer(0)),
            ForStatement('i', Integer(0), op(ref('i'), '<', Integer(3)), [
                ForStatement('j', Integer(0), op(ref('j'), '<', Integer(5)), [
                    IfStatement(op(ref('j'), '==', Integer(2)), [BreakStatement()], []),
                    Assignment('count', op(ref('count'), '+', Integer(1))),
                ]),
            ]),
            ReturnStatement(ref('count')),
        ], 6)

    def test_inner_continue_does_not_skip_outer_tail(self):
        self.run_both([
            VariableDeclaration('i32', 'i', Integer(0)),
            VariableDeclaration('i32', 'j', Integer(0)),
            VariableDeclaration('i32', 'count', Integer(0)),
            ForStatement('i', Integer(0), op(ref('i'), '<', Integer(3)), [
                ForStatement('j', Integer(0), op(ref('j'), '<', Integer(3)), [
                    IfStatement(op(ref('j'), '==', Integer(1)), [ContinueStatement()], []),
                    Assignment('count', op(ref('count'), '+', Integer(1))),
                ]),
                Assignment('count', op(ref('count'), '+', Integer(10))),
            ]),
            ReturnStatement(ref('count')),
        ], 36)

    def test_return_inside_inner_loop_exits_function(self):
        self.run_both([
            VariableDeclaration('i32', 'i', Integer(0)),
            VariableDeclaration('i32', 'j', Integer(0)),
            ForStatement('i', Integer(0), op(ref('i'), '<', Integer(4)), [
                WhileStatement(op(ref('j'), '<', Integer(3)), [
                    IfStatement(op(ref('i'), '==', Integer(2)), [
                        ReturnStatement(Integer(42)),
                        Assignment('invalid_unreachable', Integer(1)),
                    ], []),
                    Assignment('j', op(ref('j'), '+', Integer(1))),
                ]),
                Assignment('j', Integer(0)),
            ]),
            ReturnStatement(Integer(99)),
        ], 42)

    def test_continue_then_conditional_return_in_outer_loop(self):
        self.run_both([
            VariableDeclaration('i32', 'i', Integer(0)),
            ForStatement('i', Integer(0), op(ref('i'), '<', Integer(5)), [
                IfStatement(op(ref('i'), '<', Integer(2)), [ContinueStatement()], []),
                IfStatement(op(ref('i'), '==', Integer(3)), [ReturnStatement(ref('i'))], []),
            ]),
            ReturnStatement(Integer(99)),
        ], 3)


if __name__ == '__main__':
    unittest.main()
