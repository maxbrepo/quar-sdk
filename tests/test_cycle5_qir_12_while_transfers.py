"""QIR-12 regression tests for structured while transfers."""
import unittest

from frontend.quar.ast_nodes import (Assignment, BinaryOperation, BreakStatement,
    ContinueStatement, FunctionCall, IfStatement, Integer, Variable,
    VariableDeclaration, WhileStatement)
from frontend.quar.qir.program_lowering import QIRProgramLoweringError, lower_ast_program
from qrvm.qir_program_backend import compile_qir_program
from tools.qir_cycle5_03_parity import execute


def run(program):
    """Return output from a compiled QIR program."""
    return execute(compile_qir_program(lower_ast_program(program)))


def increment(name):
    """Create a one-unit increment of an existing i32 variable."""
    return Assignment(name, BinaryOperation(Variable(name), '+', Integer(1)))


class QIR12WhileTransfers(unittest.TestCase):
    def test_break_immediately(self):
        program = [VariableDeclaration('i32', 'x', Integer(0)),
                   WhileStatement(BinaryOperation(Variable('x'), '<', Integer(10)),
                                  [increment('x'), BreakStatement()]),
                   FunctionCall('print', [Variable('x')])]
        self.assertEqual(run(program), '1\n')

    def test_continue_skips_remaining_body(self):
        program = [VariableDeclaration('i32', 'x', Integer(0)),
                   VariableDeclaration('i32', 'sum', Integer(0)),
                   WhileStatement(BinaryOperation(Variable('x'), '<', Integer(5)), [
                       increment('x'),
                       IfStatement(BinaryOperation(Variable('x'), '<', Integer(3)),
                                   [ContinueStatement()], []),
                       Assignment('sum', BinaryOperation(Variable('sum'), '+', Variable('x')))]),
                   FunctionCall('print', [Variable('sum')])]
        self.assertEqual(run(program), '12\n')

    def test_break_in_conditional_branch(self):
        program = [VariableDeclaration('i32', 'x', Integer(0)),
                   WhileStatement(BinaryOperation(Variable('x'), '<', Integer(10)), [
                       increment('x'),
                       IfStatement(BinaryOperation(Variable('x'), '==', Integer(4)),
                                   [BreakStatement()], [])]),
                   FunctionCall('print', [Variable('x')])]
        self.assertEqual(run(program), '4\n')

    def test_nested_break_only_exits_inner_loop(self):
        program = [VariableDeclaration('i32', 'outer', Integer(0)),
                   VariableDeclaration('i32', 'hits', Integer(0)),
                   WhileStatement(BinaryOperation(Variable('outer'), '<', Integer(3)), [
                       increment('outer'),
                       WhileStatement(BinaryOperation(Variable('hits'), '<', Integer(20)), [
                           increment('hits'), BreakStatement()])]),
                   FunctionCall('print', [Variable('outer')]),
                   FunctionCall('print', [Variable('hits')])]
        self.assertEqual(run(program), '3\n3\n')

    def test_if_both_paths_transfer(self):
        program = [VariableDeclaration('i32', 'x', Integer(0)),
                   WhileStatement(BinaryOperation(Variable('x'), '<', Integer(5)), [
                       increment('x'),
                       IfStatement(BinaryOperation(Variable('x'), '<', Integer(3)),
                                   [ContinueStatement()], [BreakStatement()])]),
                   FunctionCall('print', [Variable('x')])]
        self.assertEqual(run(program), '3\n')

    def test_transfer_outside_loop_rejected(self):
        with self.assertRaises(QIRProgramLoweringError):
            lower_ast_program([BreakStatement()])


if __name__ == '__main__':
    unittest.main()
