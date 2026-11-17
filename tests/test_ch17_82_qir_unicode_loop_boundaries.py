"""Executable regression tests for Unicode loop boundaries and reassignment."""
import unittest

from frontend.quar.ast_nodes import (
    Assignment, BinaryOperation, ContinueStatement, ForStatement, FunctionCall,
    IfStatement, Integer, ReturnStatement, String, Variable, VariableDeclaration,
    WhileStatement,
)
from test_ch17_66_qir_array_source_integration import SourceArrayIntegrationTests


def ref(name):
    return Variable(name)


def binary(left, operator, right):
    return BinaryOperation(left, operator, right)


def intrinsic(name, *arguments):
    return FunctionCall(name, list(arguments))


class UnicodeLoopBoundaryTests(unittest.TestCase):
    run_both = SourceArrayIntegrationTests.run_both

    def test_empty_string_skips_for_body(self):
        self.run_both([
            VariableDeclaration('string', 'text', String('')),
            VariableDeclaration('i32', 'index', Integer(0)),
            VariableDeclaration('i32', 'total', Integer(17)),
            ForStatement('index', Integer(0), binary(ref('index'), '<',
                intrinsic('__qir_utf8_scalar_len', ref('text'))), [
                Assignment('total', Integer(99)),
            ]),
            ReturnStatement(ref('total')),
        ], 17)

    def test_reassigned_string_used_by_unicode_loop(self):
        self.run_both([
            VariableDeclaration('string', 'text', String('abc')),
            Assignment('text', String('é😀')),
            VariableDeclaration('i32', 'index', Integer(0)),
            VariableDeclaration('i32', 'total', Integer(0)),
            WhileStatement(binary(ref('index'), '<',
                intrinsic('__qir_utf8_scalar_len', ref('text'))), [
                IfStatement(binary(ref('index'), '==', Integer(0)), [
                    Assignment('index', binary(ref('index'), '+', Integer(1))),
                    ContinueStatement(),
                ], []),
                Assignment('total', binary(ref('total'), '+',
                    intrinsic('__qir_utf8_scalar_at', ref('text'), ref('index')))),
                Assignment('index', binary(ref('index'), '+', Integer(1))),
            ]),
            ReturnStatement(ref('total')),
        ], ord('😀'))


if __name__ == '__main__':
    unittest.main()
