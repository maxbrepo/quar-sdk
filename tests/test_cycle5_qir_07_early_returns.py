"""QIR-07: conditional early returns and mutually recursive bool functions."""
import unittest

from frontend.quar.ast_nodes import (BinaryOperation, Boolean, FunctionCall,
    FunctionDefinition, FunctionParameter, IfStatement, Integer, ReturnStatement, Variable)
from frontend.quar.qir.program_lowering import lower_ast_program, QIRProgramLoweringError
from qrvm.qir_program_backend import compile_qir_program
from tools.qir_cycle5_03_parity import execute


class QIR07EarlyReturnTests(unittest.TestCase):
    def test_mutual_recursion_bool(self):
        n = Variable('n')
        condition = BinaryOperation(n, '==', Integer(0))
        decrement = BinaryOperation(n, '-', Integer(1))
        even = FunctionDefinition('bool', 'is_even', [FunctionParameter('i32', 'n')], [
            IfStatement(condition, [ReturnStatement(Boolean(True))], []),
            ReturnStatement(FunctionCall('is_odd', [decrement]))])
        odd = FunctionDefinition('bool', 'is_odd', [FunctionParameter('i32', 'n')], [
            IfStatement(condition, [ReturnStatement(Boolean(False))], []),
            ReturnStatement(FunctionCall('is_even', [decrement]))])
        # Convert boolean results to integers through conditional branches.
        program = [even, odd, IfStatement(FunctionCall('is_even', [Integer(8)]),
            [FunctionCall('print', [Integer(1)])], [FunctionCall('print', [Integer(0)])]),
            IfStatement(FunctionCall('is_odd', [Integer(8)]),
            [FunctionCall('print', [Integer(1)])], [FunctionCall('print', [Integer(0)])])]
        self.assertEqual(execute(compile_qir_program(lower_ast_program(program))), '1\n0\n')

    def test_both_branches_return(self):
        choose = FunctionDefinition('i32', 'choose', [FunctionParameter('i32', 'x')], [
            IfStatement(BinaryOperation(Variable('x'), '==', Integer(0)),
                [ReturnStatement(Integer(11))], [ReturnStatement(Integer(22))])])
        program = [choose, FunctionCall('print', [FunctionCall('choose', [Integer(0)])]),
                   FunctionCall('print', [FunctionCall('choose', [Integer(1)])])]
        self.assertEqual(execute(compile_qir_program(lower_ast_program(program))), '11\n22\n')

    def test_return_type_mismatch_fails_closed(self):
        bad = FunctionDefinition('bool', 'bad', [], [ReturnStatement(Integer(1))])
        with self.assertRaises(QIRProgramLoweringError):
            lower_ast_program([bad, FunctionCall('print', [Integer(1)])])


if __name__ == '__main__':
    unittest.main()
