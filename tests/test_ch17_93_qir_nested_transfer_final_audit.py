"""Final audit of mixed control transfers in nested loops, through both QIR routes."""
import unittest

from frontend.quar.ast_nodes import (
    Assignment, BinaryOperation, BreakStatement, ContinueStatement, ForStatement,
    IfStatement, Integer, ReturnStatement, Variable, VariableDeclaration, WhileStatement,
)
from test_ch17_66_qir_array_source_integration import SourceArrayIntegrationTests


def ref(name):
    return Variable(name)


def binary(left, operator, right):
    return BinaryOperation(left, operator, right)


class NestedTransferFinalAuditTests(unittest.TestCase):
    run_both = SourceArrayIntegrationTests.run_both

    def test_inner_break_then_outer_continue(self):
        self.run_both([
            VariableDeclaration('i32', 'i', Integer(0)),
            VariableDeclaration('i32', 'j', Integer(0)),
            VariableDeclaration('i32', 'total', Integer(0)),
            ForStatement('i', Integer(0), binary(ref('i'), '<', Integer(4)), [
                ForStatement('j', Integer(0), binary(ref('j'), '<', Integer(4)), [
                    IfStatement(binary(ref('j'), '==', Integer(2)), [BreakStatement()], []),
                    Assignment('total', binary(ref('total'), '+', Integer(1))),
                ]),
                IfStatement(binary(ref('i'), '==', Integer(1)), [ContinueStatement()], []),
                Assignment('total', binary(ref('total'), '+', Integer(10))),
            ]),
            ReturnStatement(ref('total')),
        ], 38)

    def test_while_continue_with_nested_for_break(self):
        self.run_both([
            VariableDeclaration('i32', 'i', Integer(0)),
            VariableDeclaration('i32', 'j', Integer(0)),
            VariableDeclaration('i32', 'total', Integer(0)),
            WhileStatement(binary(ref('i'), '<', Integer(3)), [
                Assignment('i', binary(ref('i'), '+', Integer(1))),
                IfStatement(binary(ref('i'), '==', Integer(2)), [ContinueStatement()], []),
                ForStatement('j', Integer(0), binary(ref('j'), '<', Integer(4)), [
                    IfStatement(binary(ref('j'), '==', Integer(2)), [BreakStatement()], []),
                    Assignment('total', binary(ref('total'), '+', Integer(1))),
                ]),
            ]),
            ReturnStatement(ref('total')),
        ], 4)

    def test_nested_conditional_return_skips_invalid_tail(self):
        self.run_both([
            VariableDeclaration('i32', 'i', Integer(0)),
            VariableDeclaration('i32', 'j', Integer(0)),
            ForStatement('i', Integer(0), binary(ref('i'), '<', Integer(4)), [
                ForStatement('j', Integer(0), binary(ref('j'), '<', Integer(4)), [
                    IfStatement(binary(ref('j'), '==', Integer(1)), [ContinueStatement()], []),
                    IfStatement(binary(ref('i'), '==', Integer(2)), [
                        ReturnStatement(Integer(27)),
                        Assignment('unreachable_unknown', Integer(1)),
                    ], []),
                ]),
            ]),
            ReturnStatement(Integer(99)),
        ], 27)

    def test_zero_iteration_skips_nested_return(self):
        self.run_both([
            VariableDeclaration('i32', 'i', Integer(0)),
            VariableDeclaration('i32', 'j', Integer(0)),
            WhileStatement(binary(ref('i'), '<', Integer(0)), [
                ForStatement('j', Integer(0), binary(ref('j'), '<', Integer(2)), [
                    ReturnStatement(Integer(88)),
                ]),
            ]),
            ReturnStatement(Integer(12)),
        ], 12)


if __name__ == '__main__':
    unittest.main()
