"""Verify the legacy IR bridge preserves short-circuit control flow."""
import unittest

from frontend.quar.ast_nodes import BinaryOperation, FunctionDefinition, FunctionParameter, ReturnStatement, Variable
from frontend.quar.ir.builder import lower_statement
from frontend.quar.qir.ast_lowering import lower_ast_function
from frontend.quar.qir.legacy_bridge import lower_ir_function
from frontend.quar.qir.validation import validate_function


class LegacyBridgeShortCircuitTests(unittest.TestCase):
    def test_nested_boolean_parity(self):
        expressions = (
            BinaryOperation(Variable("a"), "and", Variable("b")),
            BinaryOperation(Variable("a"), "or", Variable("b")),
            BinaryOperation(Variable("a"), "and", BinaryOperation(Variable("b"), "or", Variable("c"))),
            BinaryOperation(BinaryOperation(Variable("a"), "or", Variable("b")), "and", Variable("c")),
        )
        for expression in expressions:
            with self.subTest(expression=expression):
                ast = FunctionDefinition("bool", "compute", [FunctionParameter("bool", name) for name in ("a", "b", "c")], [ReturnStatement(expression)])
                direct = lower_ast_function(ast)
                bridged = lower_ir_function(lower_statement(ast))
                validate_function(bridged)
                self.assertEqual(len(direct.blocks), len(bridged.blocks))
                self.assertEqual([type(b.terminator) for b in direct.blocks], [type(b.terminator) for b in bridged.blocks])
                self.assertEqual([len(b.phis) for b in direct.blocks], [len(b.phis) for b in bridged.blocks])


if __name__ == "__main__":
    unittest.main()
