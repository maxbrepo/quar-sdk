"""Reconcile the historical string boundary with supported QIR string lowering.

Originally this suite expected all source string variables and returns to fail.
That contract was superseded by the later string lowering implementation.
"""
import unittest

from frontend.quar.ast_nodes import FunctionDefinition, Integer, ReturnStatement, String, VariableDeclaration
from frontend.quar.ir.builder import lower_expression, lower_statement
from frontend.quar.ir.model import IRString
from frontend.quar.qir.ast_lowering import lower_ast_function
from frontend.quar.qir.legacy_bridge import lower_ir_function
from frontend.quar.qir.types import canonical_type


class StringBoundaryTests(unittest.TestCase):
    def test_string_literal_survives_legacy_ir(self):
        self.assertEqual(lower_expression(String("hello")), IRString("hello"))

    def test_string_is_a_canonical_qir_type(self):
        self.assertEqual(canonical_type("string").name, "string")

    def test_string_variable_lowers_in_both_routes(self):
        function = FunctionDefinition("i32", "string_boundary", [], [
            VariableDeclaration("string", "message", String("hello")),
            ReturnStatement(Integer(0)),
        ])
        self.assertEqual(lower_ast_function(function).return_type.name, "i32")
        self.assertEqual(lower_ir_function(lower_statement(function)).return_type.name, "i32")

    def test_string_return_type_lowers_in_both_routes(self):
        function = FunctionDefinition("string", "string_boundary", [], [
            ReturnStatement(String("hello")),
        ])
        self.assertEqual(lower_ast_function(function).return_type.name, "string")
        self.assertEqual(lower_ir_function(lower_statement(function)).return_type.name, "string")


if __name__ == "__main__":
    unittest.main()
