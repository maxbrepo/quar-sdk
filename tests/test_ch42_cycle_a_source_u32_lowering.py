"""QIR lowering of typed unsigned literals after frontend AST construction."""
import unittest
from frontend.quar.ast_nodes import (ExternalFunctionDeclaration, FunctionParameter,
                                     FunctionCall, Integer, Variable, VariableDeclaration)
from frontend.quar.qir.program_lowering import lower_ast_program, QIRProgramLoweringError
from qrvm.qir_program_backend import compile_qir_program
from qrvm.instructions import OpCode


class SourceU32LoweringTests(unittest.TestCase):
    def lower(self, literal, *, declared=True):
        declaration = ExternalFunctionDeclaration("C", "void", "native_set",
                                                  [FunctionParameter("u32", "value")])
        statements = ([VariableDeclaration("u32", "flag", Integer(literal))] if declared else [])
        statements.append(FunctionCall("native_set", [Variable("flag") if declared else Integer(literal)]))
        return lower_ast_program([declaration, *statements])

    def test_variable_maximum(self):
        package = compile_qir_program(self.lower(0xFFFFFFFF))
        self.assertIn((OpCode.PUSH_INT, 0xFFFFFFFF), package["instructions"])

    def test_direct_native_argument(self):
        compile_qir_program(self.lower(7, declared=False))

    def test_zero(self):
        compile_qir_program(self.lower(0))

    def test_negative_rejected(self):
        with self.assertRaises(QIRProgramLoweringError):
            self.lower(-1)

    def test_overflow_rejected(self):
        with self.assertRaises(QIRProgramLoweringError):
            self.lower(0x100000000)

    def test_i32_variable_not_implicitly_cast(self):
        declaration = ExternalFunctionDeclaration("C", "void", "native_set", [FunctionParameter("u32", "value")])
        with self.assertRaises(QIRProgramLoweringError):
            lower_ast_program([declaration, VariableDeclaration("i32", "flag", Integer(7)),
                               FunctionCall("native_set", [Variable("flag")])])


if __name__ == "__main__":
    unittest.main()
