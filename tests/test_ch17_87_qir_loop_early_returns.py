"""Early returns inside loops must terminate their path on both QIR routes."""
import unittest
from frontend.quar.ast_nodes import (Assignment, BinaryOperation, Boolean, ForStatement,
    IfStatement, Integer, ReturnStatement, Variable, VariableDeclaration, WhileStatement)
from test_ch17_66_qir_array_source_integration import SourceArrayIntegrationTests


def v(name):
    return Variable(name)


def cmp(a, operator, b):
    return BinaryOperation(a, operator, b)


class LoopEarlyReturnTests(unittest.TestCase):
    run_both = SourceArrayIntegrationTests.run_both

    def test_unconditional_return_in_while(self):
        self.run_both([WhileStatement(Boolean(True), [
            ReturnStatement(Integer(41))]), ReturnStatement(Integer(99))], 41)

    def test_conditional_return_in_while(self):
        self.run_both([VariableDeclaration('i32', 'i', Integer(0)),
            WhileStatement(cmp(v('i'), '<', Integer(5)), [
                IfStatement(cmp(v('i'), '==', Integer(3)), [ReturnStatement(v('i'))], []),
                Assignment('i', cmp(v('i'), '+', Integer(1)))]),
            ReturnStatement(Integer(99))], 3)

    def test_return_in_nested_for(self):
        self.run_both([VariableDeclaration('i32', 'i', Integer(0)),
            VariableDeclaration('i32', 'j', Integer(0)),
            ForStatement('i', Integer(0), cmp(v('i'), '<', Integer(3)), [
                ForStatement('j', Integer(0), cmp(v('j'), '<', Integer(3)), [
                    IfStatement(cmp(v('j'), '==', Integer(2)), [ReturnStatement(v('i'))], [])])]),
            ReturnStatement(Integer(99))], 0)

    def test_fallthrough_when_loop_skipped(self):
        self.run_both([WhileStatement(Boolean(False), [
            ReturnStatement(Integer(41))]), ReturnStatement(Integer(99))], 99)


if __name__ == '__main__':
    unittest.main()
