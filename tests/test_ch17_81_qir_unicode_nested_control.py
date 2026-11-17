"""Executable Unicode iteration regression across nested loops and transfers."""
import unittest

from frontend.quar.ast_nodes import (
    Assignment, BinaryOperation, BreakStatement, ContinueStatement,
    ForStatement, FunctionCall, IfStatement, Integer, ReturnStatement,
    String, Variable, VariableDeclaration, WhileStatement,
)
from test_ch17_66_qir_array_source_integration import SourceArrayIntegrationTests


def ref(name):
    return Variable(name)


def binary(left, operator, right):
    return BinaryOperation(left, operator, right)


def intrinsic(name, *arguments):
    return FunctionCall(name, list(arguments))


class UnicodeNestedControlTests(unittest.TestCase):
    run_both = SourceArrayIntegrationTests.run_both

    def test_nested_for_with_unicode_continue(self):
        self.run_both([
            VariableDeclaration('string', 'text', String('aé😀')),
            VariableDeclaration('i32', 'i', Integer(0)),
            VariableDeclaration('i32', 'j', Integer(0)),
            VariableDeclaration('i32', 'total', Integer(0)),
            ForStatement('i', Integer(0), binary(ref('i'), '<', Integer(2)), [
                ForStatement('j', Integer(0), binary(ref('j'), '<', intrinsic('__qir_utf8_scalar_len', ref('text'))), [
                    IfStatement(binary(ref('j'), '==', Integer(1)), [ContinueStatement()], []),
                    Assignment('total', binary(ref('total'), '+',
                        intrinsic('__qir_utf8_scalar_at', ref('text'), ref('j')))),
                ]),
            ]),
            ReturnStatement(ref('total')),
        ], 2 * (ord('a') + ord('😀')))

    def test_nested_while_with_unicode_break(self):
        self.run_both([
            VariableDeclaration('string', 'text', String('aé😀')),
            VariableDeclaration('i32', 'outer', Integer(0)),
            VariableDeclaration('i32', 'index', Integer(0)),
            VariableDeclaration('i32', 'total', Integer(0)),
            WhileStatement(binary(ref('outer'), '<', Integer(2)), [
                Assignment('index', Integer(0)),
                WhileStatement(binary(ref('index'), '<', intrinsic('__qir_utf8_scalar_len', ref('text'))), [
                    IfStatement(binary(ref('index'), '==', Integer(2)), [BreakStatement()], []),
                    Assignment('total', binary(ref('total'), '+',
                        intrinsic('__qir_utf8_scalar_at', ref('text'), ref('index')))),
                    Assignment('index', binary(ref('index'), '+', Integer(1))),
                ]),
                Assignment('outer', binary(ref('outer'), '+', Integer(1))),
            ]),
            ReturnStatement(ref('total')),
        ], 2 * (ord('a') + ord('é')))


if __name__ == '__main__':
    unittest.main()
