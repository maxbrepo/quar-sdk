"""Regression audit of nested transfer edges through both QIR compilation routes."""
import unittest

from frontend.quar.ast_nodes import (
    Assignment, BinaryOperation, BreakStatement, ContinueStatement,
    ForStatement, IfStatement, Integer, ReturnStatement, Variable,
    VariableDeclaration, WhileStatement,
)
from test_ch17_66_qir_array_source_integration import SourceArrayIntegrationTests


def ref(name):
    return Variable(name)


def binary(left, operator, right):
    return BinaryOperation(left, operator, right)


class LoopTransferEdgeAuditTests(unittest.TestCase):
    run_both = SourceArrayIntegrationTests.run_both

    def test_inner_break_preserves_outer_iteration_and_return(self):
        self.run_both([
            VariableDeclaration('i32', 'i', Integer(0)),
            VariableDeclaration('i32', 'j', Integer(0)),
            VariableDeclaration('i32', 'total', Integer(0)),
            ForStatement('i', Integer(0), binary(ref('i'), '<', Integer(5)), [
                ForStatement('j', Integer(0), binary(ref('j'), '<', Integer(5)), [
                    IfStatement(binary(ref('j'), '==', Integer(2)), [
                        BreakStatement(),
                        Assignment('invalid_after_break', Integer(1)),
                    ], []),
                    Assignment('total', binary(ref('total'), '+', Integer(1))),
                ]),
                IfStatement(binary(ref('i'), '==', Integer(3)), [
                    ReturnStatement(ref('total')),
                    Assignment('invalid_after_return', Integer(1)),
                ], []),
            ]),
            ReturnStatement(Integer(-1)),
        ], 8)

    def test_while_continue_skips_tail_and_nested_for_remains_scoped(self):
        self.run_both([
            VariableDeclaration('i32', 'i', Integer(0)),
            VariableDeclaration('i32', 'j', Integer(0)),
            VariableDeclaration('i32', 'total', Integer(0)),
            WhileStatement(binary(ref('i'), '<', Integer(5)), [
                Assignment('i', binary(ref('i'), '+', Integer(1))),
                IfStatement(binary(ref('i'), '==', Integer(3)), [
                    ContinueStatement(),
                    Assignment('invalid_after_continue', Integer(1)),
                ], []),
                ForStatement('j', Integer(0), binary(ref('j'), '<', Integer(4)), [
                    IfStatement(binary(ref('j'), '==', Integer(1)), [BreakStatement()], []),
                    Assignment('total', binary(ref('total'), '+', ref('i'))),
                ]),
            ]),
            ReturnStatement(ref('total')),
        ], 12)


if __name__ == '__main__':
    unittest.main()
