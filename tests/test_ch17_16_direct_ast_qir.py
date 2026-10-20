"""Direct AST-to-QIR and legacy-bridge structural parity tests."""
import unittest

from frontend.quar.ast_nodes import (Assignment, BinaryOperation, FunctionDefinition,
    FunctionParameter, IfStatement, Integer, ReturnStatement, Variable, VariableDeclaration)
from frontend.quar.ir.builder import lower_statement
from frontend.quar.qir.ast_lowering import QIRASTLoweringError, lower_ast_function
from frontend.quar.qir.legacy_bridge import lower_ir_function
from frontend.quar.qir.validation import validate_function


class DirectASTQIRTests(unittest.TestCase):
    def function(self, body, parameters=(), return_type="int"):
        return FunctionDefinition(return_type, "compute", list(parameters), list(body))

    def test_direct_constant(self):
        q = lower_ast_function(self.function([ReturnStatement(Integer(42))]))
        self.assertEqual(q.return_type.name, "i32")
        self.assertEqual(q.blocks[0].instructions[0].immediate, 42)
        validate_function(q)

    def test_direct_parameter_arithmetic(self):
        ast = self.function([ReturnStatement(BinaryOperation(Variable("x"), "+", Integer(3)))],
                            [FunctionParameter("int", "x")])
        q = lower_ast_function(ast)
        self.assertEqual(q.blocks[0].instructions[-1].opcode, "add")
        validate_function(q)

    def test_direct_assignment(self):
        ast = self.function([VariableDeclaration("int", "x", Integer(1)),
            Assignment("x", BinaryOperation(Variable("x"), "*", Integer(2))),
            ReturnStatement(Variable("x"))])
        q = lower_ast_function(ast)
        self.assertEqual(q.blocks[0].terminator.value, q.blocks[0].instructions[-1].result)

    def test_parity_with_existing_ir_bridge(self):
        ast = self.function([VariableDeclaration("int", "x", Integer(4)),
            Assignment("x", BinaryOperation(Variable("x"), "+", Integer(5))),
            ReturnStatement(Variable("x"))], [FunctionParameter("int", "p")])
        direct = lower_ast_function(ast)
        bridged = lower_ir_function(lower_statement(ast))
        self.assertEqual(direct.return_type, bridged.return_type)
        self.assertEqual(tuple(p.type for p in direct.parameters), tuple(p.type for p in bridged.parameters))
        self.assertEqual([(i.opcode, i.immediate) for i in direct.blocks[0].instructions],
                         [(i.opcode, i.immediate) for i in bridged.blocks[0].instructions])
        self.assertEqual(len(direct.blocks), len(bridged.blocks))

    def test_alias_and_source_unchanged(self):
        ast = self.function([ReturnStatement(Variable("x"))],
                            [FunctionParameter("Counter", "x")], "Counter")
        q = lower_ast_function(ast, type_aliases={"Counter": "long"})
        self.assertEqual(q.return_type.name, "i64")
        self.assertEqual(ast.return_type, "Counter")

    def test_reject_unsupported_control_flow(self):
        ast = self.function([IfStatement(Integer(1), [], []), ReturnStatement(Integer(0))])
        with self.assertRaises(QIRASTLoweringError):
            lower_ast_function(ast)

    def test_reject_undefined_reference(self):
        with self.assertRaises(QIRASTLoweringError):
            lower_ast_function(self.function([ReturnStatement(Variable("missing"))]))

    def test_reject_implicit_conversion(self):
        ast = self.function([ReturnStatement(Variable("x"))], [FunctionParameter("long", "x")])
        with self.assertRaises(QIRASTLoweringError):
            lower_ast_function(ast)

    def test_reject_out_of_range_literal(self):
        with self.assertRaises(QIRASTLoweringError):
            lower_ast_function(self.function([ReturnStatement(Integer(256))], return_type="u8"))

    def test_reject_default_parameter(self):
        ast = self.function([ReturnStatement(Integer(1))], [FunctionParameter("int", "x", Integer(2))])
        with self.assertRaises(QIRASTLoweringError):
            lower_ast_function(ast)

    def test_reject_missing_return(self):
        with self.assertRaises(QIRASTLoweringError):
            lower_ast_function(self.function([VariableDeclaration("int", "x", Integer(1))]))

    def test_reject_statement_after_return(self):
        with self.assertRaises(QIRASTLoweringError):
            lower_ast_function(self.function([ReturnStatement(Integer(1)), ReturnStatement(Integer(2))]))

    def test_reject_duplicate_local(self):
        ast = self.function([VariableDeclaration("int", "x", Integer(1)),
            VariableDeclaration("int", "x", Integer(2)), ReturnStatement(Variable("x"))])
        with self.assertRaises(QIRASTLoweringError):
            lower_ast_function(ast)


if __name__ == "__main__":
    unittest.main()
