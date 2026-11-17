"""Executable regression coverage for array writes across nested loop transfers."""
import unittest

from frontend.quar.ast_nodes import (
    ArrayAccess, ArrayAssignment, ArrayDeclaration, Assignment,
    BinaryOperation, BreakStatement, ContinueStatement, ForStatement,
    IfStatement, Integer, ReturnStatement, Variable, VariableDeclaration,
    WhileStatement,
)
from test_ch17_66_qir_array_source_integration import SourceArrayIntegrationTests


def var(name):
    return Variable(name)


def binary(left, operator, right):
    return BinaryOperation(left, operator, right)


class ArrayNestedControlTests(unittest.TestCase):
    run_both = SourceArrayIntegrationTests.run_both

    def test_nested_for_writes_and_inner_continue(self):
        self.run_both([
            VariableDeclaration('i32', 'i', Integer(0)),
            VariableDeclaration('i32', 'j', Integer(0)),
            ArrayDeclaration('i32', 'items', 3, [Integer(0), Integer(0), Integer(0)]),
            ForStatement('i', Integer(0), binary(var('i'), '<', Integer(3)), [
                ForStatement('j', Integer(0), binary(var('j'), '<', Integer(3)), [
                    IfStatement(binary(var('j'), '==', Integer(1)), [ContinueStatement()], []),
                    ArrayAssignment('items', var('i'), binary(
                        ArrayAccess('items', var('i')), '+', Integer(1))),
                ]),
            ]),
            ReturnStatement(ArrayAccess('items', Integer(2))),
        ], 2)

    def test_inner_break_preserves_outer_array_writes(self):
        self.run_both([
            VariableDeclaration('i32', 'i', Integer(0)),
            VariableDeclaration('i32', 'j', Integer(0)),
            ArrayDeclaration('i32', 'items', 3, [Integer(0), Integer(0), Integer(0)]),
            ForStatement('i', Integer(0), binary(var('i'), '<', Integer(3)), [
                ForStatement('j', Integer(0), binary(var('j'), '<', Integer(4)), [
                    IfStatement(binary(var('j'), '==', Integer(2)), [BreakStatement()], []),
                    ArrayAssignment('items', var('i'), binary(
                        ArrayAccess('items', var('i')), '+', Integer(1))),
                ]),
            ]),
            ReturnStatement(ArrayAccess('items', Integer(1))),
        ], 2)

    def test_while_continue_with_indexed_mutation(self):
        self.run_both([
            VariableDeclaration('i32', 'i', Integer(0)),
            ArrayDeclaration('i32', 'items', 3, [Integer(0), Integer(0), Integer(0)]),
            WhileStatement(binary(var('i'), '<', Integer(3)), [
                ArrayAssignment('items', var('i'), binary(var('i'), '+', Integer(5))),
                Assignment('i', binary(var('i'), '+', Integer(1))),
                IfStatement(binary(var('i'), '<', Integer(3)), [ContinueStatement()], []),
            ]),
            ReturnStatement(ArrayAccess('items', Integer(2))),
        ], 7)


if __name__ == '__main__':
    unittest.main()
