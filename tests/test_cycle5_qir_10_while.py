"""QIR-10 basic while-loop lowering and QRVM execution regression tests."""
import unittest

from frontend.quar.ast_nodes import (Assignment, BinaryOperation, FunctionCall,
                                     Integer, Variable, VariableDeclaration, WhileStatement)
from frontend.quar.qir.program_lowering import lower_ast_program
from qrvm.qir_program_backend import compile_qir_program
from tools.qir_cycle5_03_parity import execute


def run_loop(program):
    """Lower, compile and execute a Visual Quar AST; return printed output."""
    return execute(compile_qir_program(lower_ast_program(program)))


class QIR10WhileTests(unittest.TestCase):
    def test_multiple_iterations(self):
        program = [VariableDeclaration('i32', 'x', Integer(0)),
                   WhileStatement(BinaryOperation(Variable('x'), '<', Integer(5)),
                                  [Assignment('x', BinaryOperation(Variable('x'), '+', Integer(1)))]),
                   FunctionCall('print', [Variable('x')])]
        self.assertEqual(run_loop(program), '5\n')

    def test_zero_iterations(self):
        program = [VariableDeclaration('i32', 'x', Integer(8)),
                   WhileStatement(BinaryOperation(Variable('x'), '<', Integer(5)),
                                  [Assignment('x', Integer(99))]),
                   FunctionCall('print', [Variable('x')])]
        self.assertEqual(run_loop(program), '8\n')

    def test_nested_loops(self):
        program = [VariableDeclaration('i32', 'x', Integer(0)),
                   VariableDeclaration('i32', 'y', Integer(0)),
                   WhileStatement(BinaryOperation(Variable('x'), '<', Integer(3)), [
                       Assignment('y', Integer(0)),
                       WhileStatement(BinaryOperation(Variable('y'), '<', Integer(2)), [
                           Assignment('y', BinaryOperation(Variable('y'), '+', Integer(1)))]),
                       Assignment('x', BinaryOperation(Variable('x'), '+', Integer(1)))]),
                   FunctionCall('print', [Variable('x')]),
                   FunctionCall('print', [Variable('y')])]
        self.assertEqual(run_loop(program), '3\n2\n')


if __name__ == '__main__':
    unittest.main()
