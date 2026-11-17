"""Executable parity tests for Unicode scalar/array control-flow boundaries."""
import unittest

from frontend.quar.ast_nodes import (
    ArrayAccess, ArrayAssignment, ArrayDeclaration, Assignment, BinaryOperation,
    BreakStatement, ContinueStatement, ForStatement, FunctionCall, IfStatement,
    Integer, ReturnStatement, String, Variable, VariableDeclaration, WhileStatement,
)
from test_ch17_66_qir_array_source_integration import SourceArrayIntegrationTests


def ref(name):
    return Variable(name)


def binary(left, operator, right):
    return BinaryOperation(left, operator, right)


def scalar(text, index):
    return FunctionCall('__qir_utf8_scalar_at', [text, index])


def length(text):
    return FunctionCall('__qir_utf8_scalar_len', [text])


class UnicodeArrayControlFlowTests(unittest.TestCase):
    run_both = SourceArrayIntegrationTests.run_both

    def test_break_preserves_array_tail(self):
        self.run_both([
            VariableDeclaration('string', 'text', String('aé😀')),
            ArrayDeclaration('i32', 'items', 3, [Integer(1), Integer(2), Integer(3)]),
            VariableDeclaration('i32', 'index', Integer(0)),
            WhileStatement(binary(ref('index'), '<', length(ref('text'))), [
                IfStatement(binary(scalar(ref('text'), ref('index')), '==', Integer(ord('é'))),
                            [BreakStatement()], []),
                ArrayAssignment('items', ref('index'), scalar(ref('text'), ref('index'))),
                Assignment('index', binary(ref('index'), '+', Integer(1))),
            ]),
            ReturnStatement(binary(ArrayAccess('items', Integer(0)), '+',
                                   binary(ArrayAccess('items', Integer(1)), '+', ArrayAccess('items', Integer(2))))),
        ], ord('a') + 2 + 3)

    def test_nested_unicode_loops_with_continue_and_array_accumulation(self):
        self.run_both([
            VariableDeclaration('string', 'text', String('aé😀')),
            ArrayDeclaration('i32', 'items', 3, [Integer(0), Integer(0), Integer(0)]),
            VariableDeclaration('i32', 'outer', Integer(0)),
            VariableDeclaration('i32', 'inner', Integer(0)),
            ForStatement('outer', Integer(0), binary(ref('outer'), '<', Integer(2)), [
                ForStatement('inner', Integer(0), binary(ref('inner'), '<', length(ref('text'))), [
                    IfStatement(binary(ref('inner'), '==', Integer(1)), [ContinueStatement()], []),
                    ArrayAssignment('items', ref('inner'), binary(ArrayAccess('items', ref('inner')), '+',
                                                             scalar(ref('text'), ref('inner')))),
                ]),
            ]),
            ReturnStatement(binary(ArrayAccess('items', Integer(0)), '+',
                                   binary(ArrayAccess('items', Integer(1)), '+', ArrayAccess('items', Integer(2))))),
        ], 2 * (ord('a') + ord('😀')))

    def test_empty_string_with_nested_loop_leaves_array_unchanged(self):
        self.run_both([
            VariableDeclaration('string', 'text', String('')),
            ArrayDeclaration('i32', 'items', 1, [Integer(47)]),
            VariableDeclaration('i32', 'outer', Integer(0)),
            VariableDeclaration('i32', 'inner', Integer(0)),
            ForStatement('outer', Integer(0), binary(ref('outer'), '<', Integer(2)), [
                ForStatement('inner', Integer(0), binary(ref('inner'), '<', length(ref('text'))), [
                    ArrayAssignment('items', Integer(0), scalar(ref('text'), ref('inner'))),
                ]),
            ]),
            ReturnStatement(ArrayAccess('items', Integer(0))),
        ], 47)


if __name__ == '__main__':
    unittest.main()
