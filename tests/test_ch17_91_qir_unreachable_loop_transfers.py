"""Unreachable tails after loop transfers must not enter either QIR route."""
import unittest
from frontend.quar.ast_nodes import (Assignment, BinaryOperation, BreakStatement,
    ContinueStatement, ForStatement, IfStatement, Integer, ReturnStatement,
    Variable, VariableDeclaration, WhileStatement)
from test_ch17_66_qir_array_source_integration import SourceArrayIntegrationTests


def var(name):
    return Variable(name)


def binary(left, operator, right):
    return BinaryOperation(left, operator, right)


class UnreachableLoopTransferTests(unittest.TestCase):
    run_both = SourceArrayIntegrationTests.run_both

    def test_while_break_skips_invalid_assignment(self):
        self.run_both([
            VariableDeclaration('i32', 'i', Integer(0)),
            WhileStatement(binary(var('i'), '<', Integer(3)), [
                BreakStatement(), Assignment('undeclared', Integer(5)),
            ]),
            ReturnStatement(var('i')),
        ], 0)

    def test_while_continue_skips_invalid_assignment(self):
        self.run_both([
            VariableDeclaration('i32', 'i', Integer(0)),
            WhileStatement(binary(var('i'), '<', Integer(3)), [
                Assignment('i', binary(var('i'), '+', Integer(1))),
                ContinueStatement(), Assignment('undeclared', Integer(5)),
            ]),
            ReturnStatement(var('i')),
        ], 3)

    def test_for_terminal_break_skips_counter_update(self):
        self.run_both([
            VariableDeclaration('i32', 'i', Integer(0)),
            ForStatement('i', Integer(0), binary(var('i'), '<', Integer(5)), [
                BreakStatement(), Assignment('undeclared', Integer(5)),
            ]),
            ReturnStatement(var('i')),
        ], 0)

    def test_conditional_continue_with_unreachable_tail(self):
        self.run_both([
            VariableDeclaration('i32', 'i', Integer(0)),
            VariableDeclaration('i32', 'total', Integer(0)),
            ForStatement('i', Integer(0), binary(var('i'), '<', Integer(5)), [
                IfStatement(binary(var('i'), '<', Integer(3)), [
                    ContinueStatement(), Assignment('undeclared', Integer(5)),
                ], []),
                Assignment('total', binary(var('total'), '+', var('i'))),
            ]),
            ReturnStatement(var('total')),
        ], 7)


if __name__ == '__main__':
    unittest.main()
