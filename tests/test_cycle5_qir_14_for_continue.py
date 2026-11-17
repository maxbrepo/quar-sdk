"""QIR-14: continue in for loops updates the counter exactly once."""
import unittest
from frontend.quar.ast_nodes import (Assignment, BinaryOperation, BreakStatement,
    ContinueStatement, ForStatement, FunctionCall, IfStatement, Integer, Variable,
    VariableDeclaration, WhileStatement)
from frontend.quar.qir.program_lowering import lower_ast_program
from qrvm.qir_program_backend import compile_qir_program
from tools.qir_cycle5_03_parity import execute


def run(program):
    """Return the printed output of a compiled QIR program."""
    return execute(compile_qir_program(lower_ast_program(program)))


class QIR14ForContinue(unittest.TestCase):
    def test_unconditional_continue(self):
        program = [VariableDeclaration('i32', 'i', Integer(0)),
            ForStatement('i', Integer(0), BinaryOperation(Variable('i'), '<', Integer(5)),
                [ContinueStatement()]), FunctionCall('print', [Variable('i')])]
        self.assertEqual(run(program), '5\n')

    def test_conditional_continue_with_step(self):
        program = [VariableDeclaration('i32', 'i', Integer(0)),
            VariableDeclaration('i32', 'total', Integer(0)),
            ForStatement('i', Integer(0), BinaryOperation(Variable('i'), '<', Integer(7)), [
                IfStatement(BinaryOperation(Variable('i'), '<', Integer(4)),
                    [ContinueStatement()], []),
                Assignment('total', BinaryOperation(Variable('total'), '+', Variable('i')))], 2, 1),
            FunctionCall('print', [Variable('total')]), FunctionCall('print', [Variable('i')])]
        self.assertEqual(run(program), '10\n8\n')

    def test_nested_while_continue_does_not_increment_for(self):
        program = [VariableDeclaration('i32', 'i', Integer(0)),
            VariableDeclaration('i32', 'j', Integer(0)),
            ForStatement('i', Integer(0), BinaryOperation(Variable('i'), '<', Integer(3)), [
                WhileStatement(BinaryOperation(Variable('j'), '<', Integer(2)), [
                    Assignment('j', BinaryOperation(Variable('j'), '+', Integer(1))),
                    ContinueStatement()])]),
            FunctionCall('print', [Variable('i')]), FunctionCall('print', [Variable('j')])]
        self.assertEqual(run(program), '3\n2\n')

    def test_break_skips_update(self):
        program = [VariableDeclaration('i32', 'i', Integer(0)),
            ForStatement('i', Integer(0), BinaryOperation(Variable('i'), '<', Integer(5)), [
                IfStatement(BinaryOperation(Variable('i'), '==', Integer(2)),
                    [BreakStatement()], []), ContinueStatement()]),
            FunctionCall('print', [Variable('i')])]
        self.assertEqual(run(program), '2\n')


if __name__ == '__main__':
    unittest.main()
