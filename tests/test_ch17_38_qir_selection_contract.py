"""Guard the explicit migration boundary for switch and match statements."""
import unittest

from frontend.quar.ast_nodes import (FunctionDefinition, FunctionParameter, Integer,
                                     MatchStatement, ReturnStatement, SwitchCase,
                                     SwitchStatement, Variable)
from frontend.quar.ir.builder import lower_statement
from frontend.quar.ir.model import IRMatch, IRSwitch
from frontend.quar.qir.ast_lowering import QIRASTLoweringError, lower_ast_function
from frontend.quar.qir.legacy_bridge import QIRBridgeError, lower_ir_function


class SelectionMigrationContractTests(unittest.TestCase):
    def function_with(self, statement):
        return FunctionDefinition("i32", "choose", [FunctionParameter("i32", "x")],
                                  [statement, ReturnStatement(Integer(0))])

    def test_switch_retains_legacy_representation_and_lowers_to_qir(self):
        function = self.function_with(SwitchStatement(
            Variable("x"), [SwitchCase(Integer(1), [])], []))
        legacy = lower_statement(function)
        self.assertIsInstance(legacy.body[0], IRSwitch)
        self.assertIsNotNone(lower_ast_function(function))
        self.assertIsNotNone(lower_ir_function(legacy))

    def test_match_retains_legacy_representation_and_fails_closed_in_qir(self):
        # This test verifies the conversion boundary, not enum semantic validity.
        function = self.function_with(MatchStatement(Variable("x"), [], []))
        legacy = lower_statement(function)
        self.assertIsInstance(legacy.body[0], IRMatch)
        with self.assertRaisesRegex(QIRASTLoweringError, "MatchStatement"):
            lower_ast_function(function)
        with self.assertRaisesRegex(QIRBridgeError, "IRMatch"):
            lower_ir_function(legacy)


if __name__ == "__main__":
    unittest.main()
