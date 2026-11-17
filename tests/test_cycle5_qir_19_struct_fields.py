"""QIR-19: flat SSA representation of i32-only structure fields."""
import unittest
from frontend.quar.ast_nodes import (StructDefinition, TypeField, ObjectDeclaration,
    MemberAccess, MemberAssignment, Integer, FunctionCall, BinaryOperation,
    VariableDeclaration, Variable, WhileStatement, Assignment)
from frontend.quar.qir.program_lowering import lower_ast_program, QIRProgramLoweringError
from qrvm.qir_program_backend import compile_qir_program
from tools.qir_cycle5_03_parity import execute


def run(program):
    """Return output from the QIR/QRVM pipeline."""
    return execute(compile_qir_program(lower_ast_program(program)))


class QIR19StructFields(unittest.TestCase):
    def test_construct_and_read(self):
        program = [StructDefinition('Point', [TypeField('i32', 'x'), TypeField('i32', 'y')]),
                   ObjectDeclaration('Point', 'p', [Integer(3), Integer(8)]),
                   FunctionCall('print', [MemberAccess('p', 'y')])]
        self.assertEqual(run(program), '8\n')

    def test_modify_field(self):
        program = [StructDefinition('Counter', [TypeField('i32', 'value')]),
                   ObjectDeclaration('Counter', 'c', [Integer(1)]),
                   MemberAssignment('c', 'value', BinaryOperation(MemberAccess('c', 'value'), '+', Integer(4))),
                   FunctionCall('print', [MemberAccess('c', 'value')])]
        self.assertEqual(run(program), '5\n')

    def test_field_in_loop(self):
        program = [StructDefinition('Counter', [TypeField('i32', 'value')]),
                   ObjectDeclaration('Counter', 'c', [Integer(0)]),
                   WhileStatement(BinaryOperation(MemberAccess('c', 'value'), '<', Integer(3)), [
                       MemberAssignment('c', 'value', BinaryOperation(MemberAccess('c', 'value'), '+', Integer(1)))]),
                   FunctionCall('print', [MemberAccess('c', 'value')])]
        self.assertEqual(run(program), '3\n')

    def test_unknown_field_rejected(self):
        with self.assertRaises(QIRProgramLoweringError):
            lower_ast_program([StructDefinition('S', [TypeField('i32', 'x')]),
                               ObjectDeclaration('S', 's', [Integer(0)]),
                               FunctionCall('print', [MemberAccess('s', 'missing')])])

    def test_non_i32_field_rejected(self):
        with self.assertRaises(QIRProgramLoweringError):
            lower_ast_program([StructDefinition('S', [TypeField('f64', 'x')])])


if __name__ == '__main__':
    unittest.main()
