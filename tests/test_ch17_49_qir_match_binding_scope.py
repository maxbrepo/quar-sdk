"""Regression tests for lexical isolation of experimental enum bindings."""
import unittest

from frontend.quar.ast_nodes import (Assignment, Integer, MatchArm, MatchStatement,
                                     ReturnStatement, Variable, VariableDeclaration)
from frontend.quar.ir.builder import lower_statement
from frontend.quar.qir.ast_lowering import QIRASTLoweringError, lower_ast_function
from frontend.quar.qir.legacy_bridge import QIRBridgeError, lower_ir_function
from tests.test_ch17_48_qir_match_payload_binding import MatchPayloadBindingTests


class MatchBindingScopeTests(unittest.TestCase):
    setUp = MatchPayloadBindingTests.setUp
    function = MatchPayloadBindingTests.function

    def check_rejected(self, match, pattern):
        function = self.function()
        function.body = [match]
        with self.assertRaisesRegex(QIRASTLoweringError, pattern):
            lower_ast_function(function, enum_layout=self.layout)
        with self.assertRaisesRegex(QIRBridgeError, pattern):
            lower_ir_function(lower_statement(function), enum_layout=self.layout)

    def test_binding_cannot_be_assigned(self):
        self.match.arms[0].body = [Assignment("number", Integer(7)), ReturnStatement(Integer(0))]
        self.check_rejected(self.match, "cannot be assigned")

    def test_binding_cannot_be_redeclared(self):
        self.match.arms[0].body = [VariableDeclaration("i32", "number", Integer(3)), ReturnStatement(Integer(0))]
        self.check_rejected(self.match, "cannot be assigned or redeclared")

    def test_nested_match_fails_closed(self):
        nested = MatchStatement(Variable("tag"), [MatchArm("Error", ["number"],
                               [ReturnStatement(Variable("number"))])],
                               [ReturnStatement(Integer(-1))])
        self.match.arms[0].body = [nested]
        self.check_rejected(self.match, "Nested match")

    def test_binding_not_visible_in_other_arm(self):
        self.match.arms[1].body = [ReturnStatement(Variable("number"))]
        self.check_rejected(self.match, "(?:Unknown|undeclared|Undefined|not defined|reference)")


if __name__ == "__main__":
    unittest.main()
