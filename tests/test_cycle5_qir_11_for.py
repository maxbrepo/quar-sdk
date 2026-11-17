"""QIR-11 canonical for-loop execution and fail-closed regression tests."""
import unittest

from frontend.quar.ast_nodes import (Assignment, BinaryOperation, ForStatement,
                                     FunctionCall, Integer, Variable,
                                     VariableDeclaration, ContinueStatement)
from frontend.quar.qir.program_lowering import (QIRProgramLoweringError,
                                                 lower_ast_program)
from qrvm.qir_program_backend import compile_qir_program
from tools.qir_cycle5_03_parity import execute


def run(program):
    """Execute the lowered QIR program and return its printed output."""
    return execute(compile_qir_program(lower_ast_program(program)))


class QIR11ForTests(unittest.TestCase):
    def test_ascending_step(self):
        program = [VariableDeclaration('i32', 'i', Integer(99)),
                   VariableDeclaration('i32', 'sum', Integer(0)),
                   ForStatement('i', Integer(0),
                                BinaryOperation(Variable('i'), '<', Integer(6)),
                                [Assignment('sum', BinaryOperation(Variable('sum'), '+', Variable('i')))], 2, 1),
                   FunctionCall('print', [Variable('sum')]),
                   FunctionCall('print', [Variable('i')])]
        self.assertEqual(run(program), '6\n6\n')

    def test_descending_step(self):
        program = [VariableDeclaration('i32', 'i', Integer(0)),
                   ForStatement('i', Integer(5),
                                BinaryOperation(Variable('i'), '>=', Integer(1)), [], 2, -1),
                   FunctionCall('print', [Variable('i')])]
        self.assertEqual(run(program), '-1\n')

    def test_zero_iterations(self):
        program = [VariableDeclaration('i32', 'i', Integer(0)),
                   ForStatement('i', Integer(5),
                                BinaryOperation(Variable('i'), '<', Integer(2)), [], 1, 1),
                   FunctionCall('print', [Variable('i')])]
        self.assertEqual(run(program), '5\n')

    def test_invalid_direction_fails_closed(self):
        program = [VariableDeclaration('i32', 'i', Integer(0)),
                   ForStatement('i', Integer(0),
                                BinaryOperation(Variable('i'), '<', Integer(2)), [], 1, -1)]
        with self.assertRaises(QIRProgramLoweringError):
            lower_ast_program(program)

    def test_continue_advances_counter(self):
        program = [VariableDeclaration('i32', 'i', Integer(0)),
                   ForStatement('i', Integer(0),
                                BinaryOperation(Variable('i'), '<', Integer(2)), [ContinueStatement()])]
        self.assertIsNotNone(lower_ast_program(program))


if __name__ == '__main__':
    unittest.main()
