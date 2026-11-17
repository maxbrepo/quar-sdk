"""Regression tests for return paths across nested loops and conditional exits."""
import unittest
from frontend.quar.ast_nodes import (Assignment, BinaryOperation, Boolean, BreakStatement,
    ContinueStatement, ForStatement, IfStatement, Integer, ReturnStatement,
    Variable, VariableDeclaration, WhileStatement)
from test_ch17_66_qir_array_source_integration import SourceArrayIntegrationTests


def var(name):
    return Variable(name)


def op(left, symbol, right):
    return BinaryOperation(left, symbol, right)


class LoopReturnPathTests(unittest.TestCase):
    run_both = SourceArrayIntegrationTests.run_both

    def test_return_after_continue_in_while(self):
        self.run_both([
            VariableDeclaration('i32', 'i', Integer(0)),
            WhileStatement(op(var('i'), '<', Integer(6)), [
                Assignment('i', op(var('i'), '+', Integer(1))),
                IfStatement(op(var('i'), '<', Integer(3)), [ContinueStatement()], []),
                ReturnStatement(var('i')),
            ]),
            ReturnStatement(Integer(99)),
        ], 3)

    def test_return_after_break_in_nested_while(self):
        self.run_both([
            VariableDeclaration('i32', 'outer', Integer(0)),
            VariableDeclaration('i32', 'inner', Integer(0)),
            WhileStatement(op(var('outer'), '<', Integer(4)), [
                Assignment('inner', Integer(0)),
                WhileStatement(op(var('inner'), '<', Integer(4)), [
                    IfStatement(op(var('inner'), '==', Integer(2)), [BreakStatement()], []),
                    Assignment('inner', op(var('inner'), '+', Integer(1))),
                ]),
                IfStatement(op(var('outer'), '==', Integer(1)), [ReturnStatement(var('inner'))], []),
                Assignment('outer', op(var('outer'), '+', Integer(1))),
            ]),
            ReturnStatement(Integer(99)),
        ], 2)

    def test_return_in_for_after_continue(self):
        self.run_both([
            VariableDeclaration('i32', 'i', Integer(0)),
            ForStatement('i', Integer(0), op(var('i'), '<', Integer(5)), [
                IfStatement(op(var('i'), '<', Integer(2)), [ContinueStatement()], []),
                ReturnStatement(var('i')),
            ]),
            ReturnStatement(Integer(99)),
        ], 2)


if __name__ == '__main__':
    unittest.main()
