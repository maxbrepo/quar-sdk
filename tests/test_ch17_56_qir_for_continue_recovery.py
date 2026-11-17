"""Verify that for-owned continue edges still advance the counter."""
import unittest

from frontend.quar.ast_nodes import (Assignment, BinaryOperation, ContinueStatement,
    ForStatement, FunctionDefinition, FunctionParameter, IfStatement, Integer,
    ReturnStatement, Variable, VariableDeclaration, WhileStatement)
from frontend.quar.ir.builder import lower_statement
from frontend.quar.qir.ast_lowering import lower_ast_function
from frontend.quar.qir.legacy_bridge import lower_ir_function
from frontend.quar.qir.c_backend import emit_c_function

from test_ch17_52_qir_for_recovery import ForRecoveryTests


class ForContinueRecoveryTests(unittest.TestCase):
    execute_both = ForRecoveryTests.execute_both
    def make_continue(self, conditional):
        transfer = (IfStatement(BinaryOperation(Variable('counter'), '==', Integer(2)),
                    [ContinueStatement()], []) if conditional else ContinueStatement())
        body = [Assignment('total', BinaryOperation(Variable('total'), '+', Integer(1))), transfer] if conditional else [transfer]
        return FunctionDefinition('i32', 'for_counter', [FunctionParameter('i32', 'limit')], [
            VariableDeclaration('i32', 'counter', Integer(0)),
            VariableDeclaration('i32', 'total', Integer(0)),
            ForStatement('counter', Integer(0),
                BinaryOperation(Variable('counter'), '<', Variable('limit')), body),
            ReturnStatement(Variable('total'))])

    def test_terminal_continue_advances_counter(self):
        self.execute_both(self.make_continue(False), [(0, 0), (1, 0), (5, 0)])

    def test_conditional_continue_advances_counter(self):
        self.execute_both(self.make_continue(True), [(0, 0), (1, 1), (5, 5)])


if __name__ == '__main__':
    unittest.main()
