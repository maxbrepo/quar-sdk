"""Regression coverage for direct AST-to-QIR conditional lowering."""
import unittest

from frontend.quar.ast_nodes import (Assignment, BinaryOperation, Boolean, FunctionDefinition,
                                     FunctionParameter, IfStatement, Integer, ReturnStatement, Variable)
from frontend.quar.qir.ast_lowering import QIRASTLoweringError, lower_ast_function
from frontend.quar.qir.model import QBranch, QPhi


class QIRIfLoweringTests(unittest.TestCase):
    def test_if_else_merges_reassigned_variable(self):
        function = FunctionDefinition("i32", "select", [FunctionParameter("bool", "flag"),
                              FunctionParameter("i32", "x")], [
            IfStatement(Variable("flag"), [Assignment("x", Integer(10))],
                        [Assignment("x", Integer(20))]), ReturnStatement(Variable("x"))])
        result = lower_ast_function(function)
        self.assertTrue(any(isinstance(b.terminator, QBranch) for b in result.blocks))
        self.assertEqual(sum(len(b.phis) for b in result.blocks), 1)

    def test_if_without_else_preserves_original_value(self):
        function = FunctionDefinition("i32", "maybe", [FunctionParameter("bool", "flag"),
                              FunctionParameter("i32", "x")], [
            IfStatement(Variable("flag"), [Assignment("x", Integer(9))], []),
            ReturnStatement(Variable("x"))])
        result = lower_ast_function(function)
        self.assertEqual(sum(len(b.phis) for b in result.blocks), 1)

    def test_nested_if_and_logical_condition(self):
        function = FunctionDefinition("i32", "nested", [FunctionParameter("bool", "a"),
            FunctionParameter("bool", "b"), FunctionParameter("i32", "x")], [
            IfStatement(BinaryOperation(Variable("a"), "and", Variable("b")),
                [IfStatement(Variable("b"), [Assignment("x", Integer(1))],
                             [Assignment("x", Integer(2))])],
                [Assignment("x", Integer(3))]), ReturnStatement(Variable("x"))])
        result = lower_ast_function(function)
        self.assertGreaterEqual(sum(len(b.phis) for b in result.blocks), 2)

    def test_branch_return_is_rejected_explicitly(self):
        function = FunctionDefinition("i32", "unsupported", [FunctionParameter("bool", "flag")], [
            IfStatement(Variable("flag"), [ReturnStatement(Integer(1))], []),
            ReturnStatement(Integer(0))])
        result = lower_ast_function(function)
        self.assertEqual(sum(b.terminator.__class__.__name__ == "QReturn" for b in result.blocks), 2)


if __name__ == "__main__":
    unittest.main()
