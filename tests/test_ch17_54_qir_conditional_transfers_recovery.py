"""Conditional loop transfers must preserve SSA values in both QIR routes."""
import unittest
from frontend.quar.ast_nodes import (Assignment, BinaryOperation, BreakStatement,
    ContinueStatement, FunctionDefinition, FunctionParameter, IfStatement,
    Integer, ReturnStatement, Variable, VariableDeclaration, WhileStatement)
from tests.test_ch17_51_qir_while_recovery import WhileRecoveryTests


def var(name):
    return Variable(name)


def add(name, amount=1):
    return Assignment(name, BinaryOperation(var(name), '+', Integer(amount)))


class ConditionalTransfersRecoveryTests(unittest.TestCase):
    def test_conditional_break_and_normal_exit(self):
        function = FunctionDefinition('i32', 'conditional_break', [FunctionParameter('i32', 'limit')], [
            VariableDeclaration('i32', 'count', Integer(0)),
            WhileStatement(BinaryOperation(var('count'), '<', var('limit')), [
                add('count'),
                IfStatement(BinaryOperation(var('count'), '==', Integer(3)), [BreakStatement()], [])]),
            ReturnStatement(var('count'))])
        WhileRecoveryTests().run_both(function, [(0, 0), (2, 2), (8, 3)])

    def test_conditional_continue_preserves_back_edge(self):
        function = FunctionDefinition('i32', 'conditional_continue', [FunctionParameter('i32', 'limit')], [
            VariableDeclaration('i32', 'count', Integer(0)),
            VariableDeclaration('i32', 'total', Integer(0)),
            WhileStatement(BinaryOperation(var('count'), '<', var('limit')), [
                add('count'),
                IfStatement(BinaryOperation(var('count'), '<', Integer(3)), [ContinueStatement()], []),
                add('total', 10)]),
            ReturnStatement(var('total'))])
        WhileRecoveryTests().run_both(function, [(0, 0), (2, 0), (3, 10), (5, 30)])

    def test_both_branches_transfer(self):
        function = FunctionDefinition('i32', 'both_transfer', [FunctionParameter('i32', 'limit')], [
            VariableDeclaration('i32', 'count', Integer(0)),
            WhileStatement(BinaryOperation(var('count'), '<', var('limit')), [
                add('count'),
                IfStatement(BinaryOperation(var('count'), '==', Integer(2)),
                            [BreakStatement()], [ContinueStatement()])]),
            ReturnStatement(var('count'))])
        WhileRecoveryTests().run_both(function, [(0, 0), (1, 1), (5, 2)])


if __name__ == '__main__':
    unittest.main()
