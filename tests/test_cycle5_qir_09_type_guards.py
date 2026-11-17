"""QIR-09: prevent invalid type changes before widening numeric support."""
import unittest

from frontend.quar.ast_nodes import Assignment, Boolean, FunctionCall, Integer, Variable, VariableDeclaration
from frontend.quar.qir.program_lowering import QIRProgramLoweringError, lower_ast_program


class QIR09TypeGuardTests(unittest.TestCase):
    def test_reject_bool_initializer_for_i32(self):
        with self.assertRaisesRegex(QIRProgramLoweringError, "Declaration type mismatch"):
            lower_ast_program([VariableDeclaration("i32", "x", Boolean(True)), FunctionCall("print", [Variable("x")])])

    def test_reject_bool_reassignment_to_i32(self):
        with self.assertRaisesRegex(QIRProgramLoweringError, "Assignment type mismatch"):
            lower_ast_program([VariableDeclaration("i32", "x", Integer(1)), Assignment("x", Boolean(True))])

    def test_reject_inferred_bool_assignment_in_i32_subset(self):
        with self.assertRaisesRegex(QIRProgramLoweringError, "Inferred assignment requires i32"):
            lower_ast_program([Assignment("x", Boolean(True))], allow_inferred_declarations=True)

    def test_accept_i32_reassignment(self):
        module = lower_ast_program([VariableDeclaration("i32", "x", Integer(1)), Assignment("x", Integer(2)), FunctionCall("print", [Variable("x")])])
        self.assertEqual(module.functions[0].name, "__qir_entry")
