"""Verify i32 type inference for internal Unicode intrinsics in comparisons."""
import unittest

from frontend.quar.ast_nodes import (BinaryOperation, FunctionCall, FunctionDefinition,
    IfStatement, Integer, ReturnStatement, String, Variable, VariableDeclaration)
from frontend.quar.ir.builder import lower_statement
from frontend.quar.qir.ast_lowering import QIRASTLoweringError, lower_ast_function
from frontend.quar.qir.legacy_bridge import QIRBridgeError, lower_ir_function
from test_ch17_66_qir_array_source_integration import SourceArrayIntegrationTests


def call(name, *arguments):
    return FunctionCall(name, list(arguments))


class UnicodeComparisonTests(unittest.TestCase):
    run_both = SourceArrayIntegrationTests.run_both

    def test_length_compared_with_literal(self):
        self.run_both([
            IfStatement(BinaryOperation(call('__qir_utf8_scalar_len', String('aé😀')), '==', Integer(3)),
                        [ReturnStatement(Integer(1))], [ReturnStatement(Integer(0))]),
        ], 1)

    def test_scalar_compared_with_literal(self):
        self.run_both([
            IfStatement(BinaryOperation(call('__qir_utf8_scalar_at', String('aé😀'), Integer(1)), '==', Integer(233)),
                        [ReturnStatement(Integer(1))], [ReturnStatement(Integer(0))]),
        ], 1)

    def test_comparison_between_two_intrinsics(self):
        self.run_both([
            IfStatement(BinaryOperation(call('__qir_utf8_scalar_len', String('abc')), '==',
                                        call('__qir_utf8_scalar_at', String('\x03'), Integer(0))),
                        [ReturnStatement(Integer(1))], [ReturnStatement(Integer(0))]),
        ], 1)

    def test_unsupported_implicit_conversion_still_rejected(self):
        body = [VariableDeclaration('i64', 'wide', Integer(3)),
                IfStatement(BinaryOperation(call('__qir_utf8_scalar_len', String('abc')), '==', Variable('wide')),
                            [ReturnStatement(Integer(1))], [ReturnStatement(Integer(0))])]
        function = FunctionDefinition('int', 'demo', [], body)
        with self.assertRaises(QIRASTLoweringError):
            lower_ast_function(function)
        with self.assertRaises(QIRBridgeError):
            lower_ir_function(lower_statement(function))


if __name__ == '__main__':
    unittest.main()
