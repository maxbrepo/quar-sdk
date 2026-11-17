"""QIR-18: integration tests for fixed-size i32 arrays."""
import unittest
from frontend.quar.ast_nodes import (ArrayAccess, ArrayAssignment, ArrayDeclaration, Assignment,
    BinaryOperation, FunctionCall, Integer, Variable, VariableDeclaration, WhileStatement)
from frontend.quar.qir.program_lowering import lower_ast_program
from qrvm.qir_program_backend import compile_qir_program
from tools.qir_cycle5_03_parity import execute


def run(statements):
    """Return printed output after QIR compilation and execution."""
    return execute(compile_qir_program(lower_ast_program(statements)))


class QIR18ArrayIntegration(unittest.TestCase):
    def test_partial_initializer_preserves_size(self):
        p = [ArrayDeclaration('i32', 'a', 5, [Integer(11)]),
             FunctionCall('print', [ArrayAccess('a', Integer(4))])]
        self.assertEqual(run(p), '0\n')

    def test_rewrite_same_element(self):
        p = [ArrayDeclaration('i32', 'a', 2, []),
             ArrayAssignment('a', Integer(1), Integer(12)),
             ArrayAssignment('a', Integer(1), Integer(34)),
             FunctionCall('print', [ArrayAccess('a', Integer(1))])]
        self.assertEqual(run(p), '34\n')

    def test_expression_index(self):
        p = [ArrayDeclaration('i32', 'a', 3, [Integer(4), Integer(8), Integer(12)]),
             VariableDeclaration('i32', 'i', Integer(1)),
             FunctionCall('print', [ArrayAccess('a', BinaryOperation(Variable('i'), '+', Integer(1)))])]
        self.assertEqual(run(p), '12\n')

    def test_accumulate_array_in_while(self):
        p = [ArrayDeclaration('i32', 'a', 3, [Integer(2), Integer(3), Integer(4)]),
             VariableDeclaration('i32', 'i', Integer(0)),
             VariableDeclaration('i32', 'sum', Integer(0)),
             WhileStatement(BinaryOperation(Variable('i'), '<', Integer(3)), [
                 Assignment('sum', BinaryOperation(Variable('sum'), '+', ArrayAccess('a', Variable('i')))),
                 Assignment('i', BinaryOperation(Variable('i'), '+', Integer(1)))]),
             FunctionCall('print', [Variable('sum')])]
        self.assertEqual(run(p), '9\n')


if __name__ == '__main__':
    unittest.main()
