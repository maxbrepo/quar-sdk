"""Unreachable statements after an unconditional return must not be lowered."""
import unittest
from frontend.quar.ast_nodes import (Assignment, BinaryOperation, ForStatement,
    IfStatement, Integer, ReturnStatement, Variable, VariableDeclaration, WhileStatement)
from test_ch17_66_qir_array_source_integration import SourceArrayIntegrationTests


class UnreachableReturnTests(unittest.TestCase):
    run_both = SourceArrayIntegrationTests.run_both

    def test_function_return_skips_unreachable_assignment(self):
        self.run_both([
            ReturnStatement(Integer(17)),
            Assignment('missing', Integer(3)),
        ], 17)

    def test_while_return_skips_unreachable_body(self):
        self.run_both([
            VariableDeclaration('i32', 'i', Integer(0)),
            WhileStatement(BinaryOperation(Variable('i'), '<', Integer(3)), [
                ReturnStatement(Integer(29)),
                Assignment('missing', Integer(3)),
            ]),
            ReturnStatement(Integer(0)),
        ], 29)

    def test_conditional_return_skips_only_its_own_branch_tail(self):
        self.run_both([
            VariableDeclaration('i32', 'i', Integer(0)),
            IfStatement(BinaryOperation(Variable('i'), '==', Integer(0)), [
                ReturnStatement(Integer(41)),
                Assignment('missing', Integer(3)),
            ], [ReturnStatement(Integer(99))]),
        ], 41)

    def test_for_return_skips_unreachable_body(self):
        self.run_both([
            VariableDeclaration('i32', 'i', Integer(0)),
            ForStatement('i', Integer(0), BinaryOperation(Variable('i'), '<', Integer(3)), [
                ReturnStatement(Integer(53)),
                Assignment('missing', Integer(3)),
            ]),
            ReturnStatement(Integer(0)),
        ], 53)


if __name__ == '__main__':
    unittest.main()
