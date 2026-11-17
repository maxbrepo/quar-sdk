"""Preserve enum match semantics while QIR tagged values remain unsupported."""
import unittest

from frontend.quar.ast_nodes import (FunctionDefinition, FunctionParameter, Integer,
                                     MatchArm, MatchStatement, ReturnStatement, Variable)
from frontend.quar.ir.builder import lower_statement
from frontend.quar.ir.model import IRMatch, IRReference, IRReturn
from frontend.quar.qir.ast_lowering import QIRASTLoweringError, lower_ast_function
from frontend.quar.qir.legacy_bridge import QIRBridgeError, lower_ir_function


class MatchMigrationContractTests(unittest.TestCase):
    def make_function(self):
        return FunctionDefinition(
            "i32", "choose", [FunctionParameter("i32", "x")],
            [MatchStatement(
                Variable("x"),
                [MatchArm("Some", ["value"], [ReturnStatement(Integer(1))]),
                 MatchArm("None", [], [ReturnStatement(Integer(2))])],
                [ReturnStatement(Integer(3))])])

    def test_legacy_ir_preserves_variant_order_bindings_and_default(self):
        ir = lower_statement(self.make_function())
        match = ir.body[0]
        self.assertIsInstance(match, IRMatch)
        self.assertIsInstance(match.expression, IRReference)
        self.assertEqual([arm.variant_name for arm in match.arms], ["Some", "None"])
        self.assertEqual(match.arms[0].bindings, ("value",))
        self.assertEqual(match.arms[1].bindings, ())
        self.assertIsInstance(match.arms[0].body[0], IRReturn)
        self.assertIsInstance(match.default_body[0], IRReturn)

    def test_qir_rejects_payload_match_in_both_routes(self):
        ast = self.make_function()
        with self.assertRaisesRegex(QIRASTLoweringError, "MatchStatement"):
            lower_ast_function(ast)
        with self.assertRaisesRegex(QIRBridgeError, "IRMatch"):
            lower_ir_function(lower_statement(ast))


if __name__ == "__main__":
    unittest.main()
