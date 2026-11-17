"""QIR pass 1: fixed-size i32 arrays, bounds and mutable indices."""
import unittest
from frontend.quar.ast_nodes import (ArrayAccess, ArrayAssignment, ArrayDeclaration,
    Assignment, BinaryOperation, FunctionCall, Integer, Variable, VariableDeclaration, WhileStatement)
from frontend.quar.qir.program_lowering import lower_ast_program, QIRProgramLoweringError
from qrvm.qir_program_backend import compile_qir_program
from tools.qir_cycle5_03_parity import execute


def run(statements):
    """Compile and execute a QIR program, returning its printed output."""
    return execute(compile_qir_program(lower_ast_program(statements)))


class QIR17ArrayCore(unittest.TestCase):
    def test_initializers_and_zero_fill(self):
        program = [ArrayDeclaration('i32', 'a', 4, [Integer(7), Integer(9)]),
            FunctionCall('print', [ArrayAccess('a', Integer(0))]),
            FunctionCall('print', [ArrayAccess('a', Integer(3))])]
        self.assertEqual(run(program), '7\n0\n')

    def test_variable_index_write(self):
        program = [ArrayDeclaration('i32', 'a', 3, []),
            VariableDeclaration('i32', 'i', Integer(1)),
            ArrayAssignment('a', Variable('i'), Integer(42)),
            FunctionCall('print', [ArrayAccess('a', Variable('i'))])]
        self.assertEqual(run(program), '42\n')

    def test_loop_writes(self):
        program = [ArrayDeclaration('i32', 'a', 3, []),
            VariableDeclaration('i32', 'i', Integer(0)),
            WhileStatement(BinaryOperation(Variable('i'), '<', Integer(3)), [
                ArrayAssignment('a', Variable('i'), Variable('i')),
                Assignment('i', BinaryOperation(Variable('i'), '+', Integer(1)))]),
            FunctionCall('print', [ArrayAccess('a', Integer(2))])]
        self.assertEqual(run(program), '2\n')

    def test_reject_oversized_initializer(self):
        with self.assertRaises(QIRProgramLoweringError):
            lower_ast_program([ArrayDeclaration('i32', 'a', 1, [Integer(1), Integer(2)])])

    def test_reject_unknown_array(self):
        with self.assertRaises(QIRProgramLoweringError):
            lower_ast_program([FunctionCall('print', [ArrayAccess('missing', Integer(0))])])


if __name__ == '__main__':
    unittest.main()
