"""Executable parity checks for indexed writes inside structured loops."""
import unittest

from frontend.quar.ast_nodes import (ArrayAccess, ArrayAssignment, ArrayDeclaration,
    Assignment, BinaryOperation, ForStatement, FunctionDefinition, IfStatement,
    Integer, ReturnStatement, Variable, VariableDeclaration, WhileStatement)
from test_ch17_66_qir_array_source_integration import SourceArrayIntegrationTests


def v(name):
    return Variable(name)


def op(left, symbol, right):
    return BinaryOperation(left, symbol, right)


class ArrayLoopMutationTests(unittest.TestCase):
    run_both = SourceArrayIntegrationTests.run_both

    def test_for_indexed_writes(self):
        self.run_both([
            VariableDeclaration('i32', 'i', Integer(0)),
            ArrayDeclaration('i32', 'items', 3, [Integer(0), Integer(0), Integer(0)]),
            ForStatement('i', Integer(0), op(v('i'), '<', Integer(3)), [
                ArrayAssignment('items', v('i'), op(v('i'), '+', Integer(10)))]),
            ReturnStatement(ArrayAccess('items', Integer(2)))], 12)

    def test_while_indexed_writes(self):
        self.run_both([
            VariableDeclaration('i32', 'i', Integer(0)),
            ArrayDeclaration('i32', 'items', 3, [Integer(0), Integer(0), Integer(0)]),
            WhileStatement(op(v('i'), '<', Integer(3)), [
                ArrayAssignment('items', v('i'), op(v('i'), '+', Integer(5))),
                Assignment('i', op(v('i'), '+', Integer(1)))]),
            ReturnStatement(ArrayAccess('items', Integer(1)))], 6)

    def test_conditional_indexed_writes(self):
        self.run_both([
            VariableDeclaration('i32', 'i', Integer(0)),
            ArrayDeclaration('i32', 'items', 3, [Integer(1), Integer(1), Integer(1)]),
            ForStatement('i', Integer(0), op(v('i'), '<', Integer(3)), [
                IfStatement(op(v('i'), '>=', Integer(1)),
                    [ArrayAssignment('items', v('i'), Integer(9))], [])]),
            ReturnStatement(ArrayAccess('items', Integer(2)))], 9)


if __name__ == '__main__':
    unittest.main()
