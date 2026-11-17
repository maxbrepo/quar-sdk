"""QIR-16: integer division and remainder through the QIR program backend."""
import unittest

from frontend.quar.ast_nodes import BinaryOperation, FunctionCall, Integer, Variable, VariableDeclaration
from frontend.quar.qir.program_lowering import lower_ast_program
from qrvm.qir_program_backend import compile_qir_program
from tools.qir_cycle5_03_parity import execute


def run(statements):
    """Compile and execute an AST program; return its printed output."""
    return execute(compile_qir_program(lower_ast_program(statements)))


class QIR16DivisionModulo(unittest.TestCase):
    def test_division(self):
        self.assertEqual(run([FunctionCall('print', [BinaryOperation(Integer(17), '/', Integer(5))])]), '3\n')

    def test_modulo(self):
        self.assertEqual(run([FunctionCall('print', [BinaryOperation(Integer(17), '%', Integer(5))])]), '2\n')

    def test_variable_operands(self):
        statements = [VariableDeclaration('i32', 'a', Integer(20)),
                      VariableDeclaration('i32', 'b', Integer(6)),
                      FunctionCall('print', [BinaryOperation(Variable('a'), '/', Variable('b'))]),
                      FunctionCall('print', [BinaryOperation(Variable('a'), '%', Variable('b'))])]
        self.assertEqual(run(statements), '3\n2\n')


if __name__ == '__main__':
    unittest.main()
