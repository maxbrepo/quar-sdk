"""Execute Unicode code-point iteration with structured loops on both QIR routes."""
import unittest

from frontend.quar.ast_nodes import (Assignment, BinaryOperation, FunctionCall,
    Integer, ReturnStatement, String, Variable, VariableDeclaration,
    WhileStatement)
from test_ch17_66_qir_array_source_integration import SourceArrayIntegrationTests


def ref(name):
    return Variable(name)


def call(name, *arguments):
    return FunctionCall(name, list(arguments))


def binary(left, operator, right):
    return BinaryOperation(left, operator, right)


class UnicodeLoopIntegrationTests(unittest.TestCase):
    run_both = SourceArrayIntegrationTests.run_both

    def test_unicode_code_point_sum(self):
        self.run_both([
            VariableDeclaration('string', 'text', String('aé😀')),
            VariableDeclaration('i32', 'index', Integer(0)),
            VariableDeclaration('i32', 'total', Integer(0)),
            WhileStatement(binary(ref('index'), '<', call('__qir_utf8_scalar_len', ref('text'))), [
                Assignment('total', binary(ref('total'), '+',
                    call('__qir_utf8_scalar_at', ref('text'), ref('index')))),
                Assignment('index', binary(ref('index'), '+', Integer(1))),
            ]),
            ReturnStatement(ref('total')),
        ], sum(map(ord, 'aé😀')))

    def test_empty_unicode_string_skips_loop(self):
        self.run_both([
            VariableDeclaration('string', 'text', String('')),
            VariableDeclaration('i32', 'index', Integer(0)),
            WhileStatement(binary(ref('index'), '<', call('__qir_utf8_scalar_len', ref('text'))), [
                Assignment('index', binary(ref('index'), '+', Integer(1))),
            ]),
            ReturnStatement(ref('index')),
        ], 0)

    def test_combining_and_embedded_nul(self):
        self.run_both([
            VariableDeclaration('string', 'text', String('e\u0301\x00')),
            VariableDeclaration('i32', 'index', Integer(0)),
            VariableDeclaration('i32', 'count', Integer(0)),
            WhileStatement(binary(ref('index'), '<', call('__qir_utf8_scalar_len', ref('text'))), [
                Assignment('count', binary(ref('count'), '+',
                    call('__qir_utf8_scalar_at', ref('text'), ref('index')))),
                Assignment('index', binary(ref('index'), '+', Integer(1))),
            ]),
            ReturnStatement(ref('count')),
        ], sum(map(ord, 'e\u0301\x00')))


if __name__ == '__main__':
    unittest.main()
