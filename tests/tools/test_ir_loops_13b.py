"""Differential checks for loop lowering and execution on the existing QRVM."""
import unittest
from frontend.quar.ast_nodes import (Integer, Variable, BinaryOperation, Assignment,
    VariableDeclaration, ForStatement, LoopStatement, DoWhileStatement,
    BreakStatement, ContinueStatement, IfStatement)
from frontend.quar.ir.builder import lower_statement
from qrvm.ir_bridge import compile_ir_statements
from qrvm.compiler import QRVMCompiler
from qrvm.vm import QRVM

class IRLoopTests(unittest.TestCase):
    def compare(self, statements, variable, expected):
        original = QRVMCompiler().compile(statements)
        converted = compile_ir_statements(tuple(lower_statement(x) for x in statements))
        self.assertEqual(original['instructions'], converted['instructions'])
        left, right = QRVM(), QRVM()
        left.run(original)
        right.run(converted)
        self.assertEqual(left.variables, right.variables)
        self.assertEqual(right.variables[variable], expected)

    def test_for_with_continue(self):
        statements = [VariableDeclaration('int', 'total', Integer(0)),
            ForStatement('i', Integer(0), BinaryOperation(Variable('i'), '<', Integer(5)), [
                IfStatement(BinaryOperation(Variable('i'), '==', Integer(2)), [ContinueStatement()], []),
                Assignment('total', BinaryOperation(Variable('total'), '+', Integer(1)))])]
        self.compare(statements, 'total', 4)

    def test_loop_with_break(self):
        statements = [VariableDeclaration('int', 'counter', Integer(0)), LoopStatement([
            Assignment('counter', BinaryOperation(Variable('counter'), '+', Integer(1))),
            IfStatement(BinaryOperation(Variable('counter'), '>=', Integer(3)), [BreakStatement()], [])])]
        self.compare(statements, 'counter', 3)

    def test_do_while(self):
        statements = [VariableDeclaration('int', 'counter', Integer(0)), DoWhileStatement([
            Assignment('counter', BinaryOperation(Variable('counter'), '+', Integer(1)))],
            BinaryOperation(Variable('counter'), '<', Integer(3)))]
        self.compare(statements, 'counter', 3)
