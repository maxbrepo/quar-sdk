"""Tests for opt-in local type inference before direct QIR lowering."""
import unittest

from frontend.quar.ast_nodes import (Assignment, BinaryOperation, FunctionDefinition,
    FunctionParameter, Integer, ReturnStatement, Variable, VariableDeclaration)
from frontend.quar.qir.inference_bridge import QIRInferenceError, lower_resolved_ast_function
from frontend.quar.qir.ast_lowering import lower_ast_function


class InferenceBridgeTests(unittest.TestCase):
    def function(self, body, parameters=(), return_type="int"):
        return FunctionDefinition(return_type, "compute", list(parameters), list(body))

    def test_inferred_literal(self):
        q = lower_resolved_ast_function(self.function([
            VariableDeclaration(None, "x", Integer(8)), ReturnStatement(Variable("x"))]))
        self.assertEqual(q.return_type.name, "i32")

    def test_inferred_from_typed_parameter(self):
        q = lower_resolved_ast_function(self.function([
            VariableDeclaration("auto", "x", Variable("p")), ReturnStatement(Variable("x"))],
            [FunctionParameter("long", "p")], "long"))
        self.assertEqual(q.return_type.name, "i64")

    def test_mixed_declarations(self):
        q = lower_resolved_ast_function(self.function([
            VariableDeclaration("int", "x", Integer(4)),
            VariableDeclaration("auto", "y", BinaryOperation(Variable("x"), "+", Integer(5))),
            ReturnStatement(Variable("y"))]))
        self.assertEqual(q.blocks[0].instructions[-1].opcode, "add")

    def test_fully_typed_matches_existing_lowerer(self):
        ast = self.function([VariableDeclaration("int", "x", Integer(2)), ReturnStatement(Variable("x"))])
        self.assertEqual(lower_resolved_ast_function(ast), lower_ast_function(ast))

    def test_ast_unchanged(self):
        ast = self.function([VariableDeclaration(None, "x", Integer(2)), ReturnStatement(Variable("x"))])
        lower_resolved_ast_function(ast)
        self.assertIsNone(ast.body[0].var_type)

    def test_reject_unknown_reference(self):
        with self.assertRaises(QIRInferenceError):
            lower_resolved_ast_function(self.function([
                VariableDeclaration("auto", "x", Variable("missing")), ReturnStatement(Integer(1))]))

    def test_reject_ambiguous_mixed_types(self):
        with self.assertRaises(QIRInferenceError):
            lower_resolved_ast_function(self.function([
                VariableDeclaration("auto", "x", BinaryOperation(Variable("a"), "+", Variable("b"))),
                ReturnStatement(Integer(1))],
                [FunctionParameter("int", "a"), FunctionParameter("long", "b")]))

    def test_reject_inferred_parameter(self):
        with self.assertRaises(QIRInferenceError):
            lower_resolved_ast_function(self.function([ReturnStatement(Integer(1))],
                [FunctionParameter("auto", "x")]))

    def test_reject_duplicate_local(self):
        with self.assertRaises(QIRInferenceError):
            lower_resolved_ast_function(self.function([
                VariableDeclaration("auto", "x", Integer(1)),
                VariableDeclaration("auto", "x", Integer(2)), ReturnStatement(Variable("x"))]))

    def test_reject_out_of_range_literal(self):
        with self.assertRaises(QIRInferenceError):
            lower_resolved_ast_function(self.function([
                VariableDeclaration("u8", "x", Integer(300)), ReturnStatement(Integer(1))]))


if __name__ == "__main__":
    unittest.main()
