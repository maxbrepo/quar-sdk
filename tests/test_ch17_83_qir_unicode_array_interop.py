"""Executable parity checks for Unicode scalars stored in fixed i32 arrays."""
import unittest

from frontend.quar.ast_nodes import (
    ArrayAccess, ArrayAssignment, ArrayDeclaration, Assignment, BinaryOperation,
    ContinueStatement, ForStatement, FunctionCall, IfStatement, Integer,
    ReturnStatement, String, Variable, VariableDeclaration, WhileStatement,
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


class UnicodeArrayInteropTests(unittest.TestCase):
    run_both = SourceArrayIntegrationTests.run_both

    def test_store_multibyte_scalars_in_fixed_array(self):
        self.run_both([
            VariableDeclaration('string', 'text', String('aé😀')),
            ArrayDeclaration('i32', 'scalars', 3, [Integer(0), Integer(0), Integer(0)]),
            VariableDeclaration('i32', 'index', Integer(0)),
            ForStatement('index', Integer(0), binary(ref('index'), '<', length(ref('text'))), [
                ArrayAssignment('scalars', ref('index'), scalar(ref('text'), ref('index'))),
            ]),
            ReturnStatement(binary(ArrayAccess('scalars', Integer(1)), '+',
                                   ArrayAccess('scalars', Integer(2)))),
        ], ord('é') + ord('😀'))

    def test_empty_unicode_loop_preserves_array(self):
        self.run_both([
            VariableDeclaration('string', 'text', String('')),
            ArrayDeclaration('i32', 'scalars', 1, [Integer(73)]),
            VariableDeclaration('i32', 'index', Integer(0)),
            WhileStatement(binary(ref('index'), '<', length(ref('text'))), [
                ArrayAssignment('scalars', Integer(0), scalar(ref('text'), ref('index'))),
                Assignment('index', binary(ref('index'), '+', Integer(1))),
            ]),
            ReturnStatement(ArrayAccess('scalars', Integer(0))),
        ], 73)

    def test_continue_preserves_unwritten_array_element(self):
        self.run_both([
            VariableDeclaration('string', 'text', String('aé😀')),
            ArrayDeclaration('i32', 'scalars', 3, [Integer(5), Integer(7), Integer(11)]),
            VariableDeclaration('i32', 'index', Integer(0)),
            ForStatement('index', Integer(0), binary(ref('index'), '<', length(ref('text'))), [
                IfStatement(binary(scalar(ref('text'), ref('index')), '==', Integer(ord('é'))),
                            [ContinueStatement()], []),
                ArrayAssignment('scalars', ref('index'), scalar(ref('text'), ref('index'))),
            ]),
            ReturnStatement(binary(ArrayAccess('scalars', Integer(0)), '+',
                                   ArrayAccess('scalars', Integer(1)))),
        ], ord('a') + 7)


if __name__ == '__main__':
    unittest.main()
