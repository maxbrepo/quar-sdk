"""QIR-07: void calls, explicit returns, and implicit fallthrough."""
import unittest
from frontend.quar.ast_nodes import FunctionDefinition, FunctionParameter, FunctionCall, Integer, ReturnStatement, Variable, IfStatement, Boolean
from frontend.quar.qir.program_lowering import lower_ast_program, QIRProgramLoweringError
from qrvm.qir_program_backend import compile_qir_program
from tools.qir_cycle5_03_parity import execute

class QIR07VoidTests(unittest.TestCase):
    def test_void_function_explicit_return(self):
        program = [FunctionDefinition('void', 'show', [FunctionParameter('i32', 'n')], [
            FunctionCall('print', [Variable('n')]), ReturnStatement(None)]),
            FunctionCall('show', [Integer(9)])]
        self.assertEqual(execute(compile_qir_program(lower_ast_program(program))), '9\n')

    def test_void_function_implicit_return(self):
        program = [FunctionDefinition('void', 'show', [], [FunctionCall('print', [Integer(7)])]),
                   FunctionCall('show', [])]
        self.assertEqual(execute(compile_qir_program(lower_ast_program(program))), '7\n')

    def test_void_conditional_return(self):
        program = [FunctionDefinition('void', 'show', [FunctionParameter('i32', 'n')], [
            IfStatement(Boolean(True), [ReturnStatement(None)], []),
            FunctionCall('print', [Variable('n')])]),
            FunctionCall('show', [Integer(3)])]
        self.assertEqual(execute(compile_qir_program(lower_ast_program(program))), '')

    def test_void_value_rejected(self):
        program = [FunctionDefinition('void', 'bad', [], [ReturnStatement(Integer(1))]),
                   FunctionCall('bad', [])]
        with self.assertRaises(QIRProgramLoweringError):
            lower_ast_program(program)

if __name__ == '__main__':
    unittest.main()
