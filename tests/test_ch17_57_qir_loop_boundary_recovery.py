"""Regression tests for loop-transfer ownership and counter updates."""
import unittest

from frontend.quar.ast_nodes import (
    Assignment, BinaryOperation, BreakStatement, ContinueStatement,
    ForStatement, FunctionDefinition, FunctionParameter, IfStatement,
    Integer, ReturnStatement, Variable, VariableDeclaration, WhileStatement,
)
from frontend.quar.ir.builder import lower_statement
from frontend.quar.qir.ast_lowering import QIRASTLoweringError, lower_ast_function
from frontend.quar.qir.legacy_bridge import QIRBridgeError, lower_ir_function
from test_ch17_52_qir_for_recovery import ForRecoveryTests


class LoopBoundaryRecoveryTests(unittest.TestCase):
    execute_both = ForRecoveryTests.execute_both

    def make_function(self, body, *, step=1):
        return FunctionDefinition('i32', 'for_counter',
            [FunctionParameter('i32', 'limit')], [
                VariableDeclaration('i32', 'counter', Integer(0)),
                VariableDeclaration('i32', 'total', Integer(0)),
                ForStatement('counter', Integer(0),
                    BinaryOperation(Variable('counter'), '<', Variable('limit')),
                    body, step),
                ReturnStatement(Variable('total'))])

    def test_conditional_continue_skips_tail_and_advances_by_two(self):
        function = self.make_function([
            IfStatement(BinaryOperation(Variable('counter'), '==', Integer(2)),
                        [ContinueStatement()], []),
            Assignment('total', BinaryOperation(Variable('total'), '+', Integer(1))),
        ], step=2)
        self.execute_both(function, [(0, 0), (1, 1), (5, 2), (8, 3)])

    def test_conditional_break_preserves_prior_accumulation(self):
        function = self.make_function([
            IfStatement(BinaryOperation(Variable('counter'), '==', Integer(3)),
                        [BreakStatement()], []),
            Assignment('total', BinaryOperation(Variable('total'), '+', Integer(1))),
        ])
        self.execute_both(function, [(0, 0), (2, 2), (5, 3)])

    def test_nested_loop_break_is_owned_by_inner_loop(self):
        function = FunctionDefinition('i32', 'for_counter',
            [FunctionParameter('i32', 'limit')], [
                VariableDeclaration('i32', 'counter', Integer(0)),
                VariableDeclaration('i32', 'inner', Integer(0)),
                VariableDeclaration('i32', 'total', Integer(0)),
                ForStatement('counter', Integer(0),
                    BinaryOperation(Variable('counter'), '<', Variable('limit')), [
                        Assignment('inner', Integer(0)),
                        WhileStatement(BinaryOperation(Variable('inner'), '<', Integer(3)), [
                            Assignment('total', BinaryOperation(Variable('total'), '+', Integer(1))),
                            BreakStatement(),
                        ]),
                    ]),
                ReturnStatement(Variable('total'))])
        self.execute_both(function, [(0, 0), (1, 1), (3, 3)])


if __name__ == '__main__':
    unittest.main()
