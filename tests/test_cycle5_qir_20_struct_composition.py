"""QIR-20: compose i32 structure fields with branches and functions."""
import unittest

from frontend.quar.ast_nodes import (
    BinaryOperation, FunctionCall, FunctionDefinition, IfStatement, Integer,
    MemberAccess, MemberAssignment, ObjectDeclaration, ReturnStatement,
    StructDefinition, TypeField, Variable,
)
from frontend.quar.qir.program_lowering import lower_ast_program
from qrvm.qir_program_backend import compile_qir_program
from tools.qir_cycle5_03_parity import execute


def run(statements):
    """Return the QRVM output for a lowered AST program."""
    return execute(compile_qir_program(lower_ast_program(statements)))


class QIR20StructComposition(unittest.TestCase):
    def test_field_modified_in_if(self):
        program = [
            StructDefinition('Counter', [TypeField('i32', 'value')]),
            ObjectDeclaration('Counter', 'c', [Integer(2)]),
            IfStatement(
                BinaryOperation(MemberAccess('c', 'value'), '<', Integer(3)),
                [MemberAssignment('c', 'value', Integer(7))],
                [MemberAssignment('c', 'value', Integer(9))],
            ),
            FunctionCall('print', [MemberAccess('c', 'value')]),
        ]
        self.assertEqual(run(program), '7\n')


if __name__ == '__main__':
    unittest.main()
