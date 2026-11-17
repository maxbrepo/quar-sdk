"""Execute terminal while transfers through both QIR routes and the C backend."""
import unittest
from tests.test_ch17_51_qir_while_recovery import WhileRecoveryTests
from frontend.quar.ast_nodes import (Assignment, BinaryOperation, BreakStatement,
    ContinueStatement, FunctionDefinition, FunctionParameter, Integer,
    ReturnStatement, Variable, VariableDeclaration, WhileStatement)
from frontend.quar.ir.builder import lower_statement
from frontend.quar.qir.ast_lowering import lower_ast_function, QIRASTLoweringError
from frontend.quar.qir.legacy_bridge import lower_ir_function, QIRBridgeError


class TerminalTransferRecoveryTests(unittest.TestCase):
    def test_terminal_break_preserves_exit_value(self):
        function = FunctionDefinition('i32', 'terminal_break', [FunctionParameter('i32', 'limit')], [
            VariableDeclaration('i32', 'counter', Integer(0)),
            WhileStatement(BinaryOperation(Variable('counter'), '<', Variable('limit')), [
                Assignment('counter', BinaryOperation(Variable('counter'), '+', Integer(1))),
                BreakStatement()]),
            ReturnStatement(Variable('counter'))])
        WhileRecoveryTests().run_both(function, [(0, 0), (1, 1), (5, 1)])

    def test_terminal_continue_rechecks_condition(self):
        function = FunctionDefinition('i32', 'terminal_continue', [FunctionParameter('i32', 'limit')], [
            VariableDeclaration('i32', 'counter', Integer(0)),
            WhileStatement(BinaryOperation(Variable('counter'), '<', Variable('limit')), [
                Assignment('counter', BinaryOperation(Variable('counter'), '+', Integer(1))),
                ContinueStatement()]),
            ReturnStatement(Variable('counter'))])
        WhileRecoveryTests().run_both(function, [(0, 0), (1, 1), (5, 5)])

    def test_nonterminal_transfer_skips_unreachable_tail(self):
        function = FunctionDefinition('i32', 'invalid_transfer', [], [
            VariableDeclaration('i32', 'counter', Integer(0)),
            WhileStatement(BinaryOperation(Variable('counter'), '<', Integer(2)), [
                BreakStatement(), Assignment('counter', Integer(1))]),
            ReturnStatement(Variable('counter'))])
        # Chapter 4.39: a transfer terminates its path, so the tail is dead.
        WhileRecoveryTests().run_both(function, [(0, 0)])
