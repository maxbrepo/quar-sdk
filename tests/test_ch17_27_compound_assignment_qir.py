"""Regression checks for compound assignment desugaring into QIR."""
import unittest

from frontend.quar.ast_nodes import (Assignment, BinaryOperation, FunctionDefinition,
    FunctionParameter, Integer, ReturnStatement, Variable)
from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from frontend.quar.ir.builder import lower_statement
from frontend.quar.qir.ast_lowering import lower_ast_function
from frontend.quar.qir.legacy_bridge import lower_ir_function
from frontend.quar.qir.validation import validate_function


class CompoundAssignmentQIRTests(unittest.TestCase):
    def test_compound_assignment_matches_explicit_binary_assignment(self):
        for symbol, opcode in (("+=", "add"), ("-=", "sub"), ("*=", "mul"),
                               ("/=", "div"), ("%=", "mod")):
            with self.subTest(operator=symbol):
                parsed = Parser(Lexer(f"x {symbol} 3;").tokenize()).parse()[0]
                self.assertIsInstance(parsed, Assignment)
                self.assertIsInstance(parsed.value, BinaryOperation)
                self.assertEqual(parsed.value.operator, symbol[:-1])
                self.assertEqual(parsed.value.left, Variable("x"))
                function = FunctionDefinition("int", "compute", [FunctionParameter("int", "x")],
                    [parsed, ReturnStatement(Variable("x"))])
                direct = lower_ast_function(function)
                bridged = lower_ir_function(lower_statement(function))
                validate_function(direct)
                validate_function(bridged)
                self.assertEqual([i.opcode for i in direct.blocks[0].instructions],
                                 [i.opcode for i in bridged.blocks[0].instructions])
                self.assertEqual(direct.blocks[0].instructions[-1].opcode, opcode)


if __name__ == "__main__":
    unittest.main()
