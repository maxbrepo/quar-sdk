"""QIR-13 for-loop break semantics on the shared while CFG."""
import unittest
from frontend.quar.ast_nodes import (Assignment, BinaryOperation, BreakStatement,
    ForStatement, FunctionCall, IfStatement, Integer, Variable, VariableDeclaration)
from frontend.quar.qir.program_lowering import lower_ast_program
from qrvm.qir_program_backend import compile_qir_program
from tools.qir_cycle5_03_parity import execute


def run(program):
    """Compile and run QIR, returning printed output."""
    return execute(compile_qir_program(lower_ast_program(program)))


class QIR13ForBreak(unittest.TestCase):
    def test_break_exits_without_increment(self):
        program = [VariableDeclaration('i32', 'i', Integer(0)),
                   ForStatement('i', Integer(0),
                       BinaryOperation(Variable('i'), '<', Integer(10)),
                       [BreakStatement()]),
                   FunctionCall('print', [Variable('i')])]
        self.assertEqual(run(program), '0\n')

    def test_conditional_break(self):
        program = [VariableDeclaration('i32', 'i', Integer(0)),
                   ForStatement('i', Integer(0),
                       BinaryOperation(Variable('i'), '<', Integer(10)),
                       [IfStatement(BinaryOperation(Variable('i'), '==', Integer(3)),
                                    [BreakStatement()], [])]),
                   FunctionCall('print', [Variable('i')])]
        self.assertEqual(run(program), '3\n')


if __name__ == '__main__':
    unittest.main()
