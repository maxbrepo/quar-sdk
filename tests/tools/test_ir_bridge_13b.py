import unittest
from frontend.quar.ast_nodes import (Boolean, Integer, Variable, BinaryOperation, Assignment, VariableDeclaration, IfStatement, WhileStatement)
from frontend.quar.ir.builder import lower_statement
from qrvm.ir_bridge import compile_ir_statements
from qrvm.compiler import QRVMCompiler

class IRBridgeTests(unittest.TestCase):
    def test_control_flow_bytecode_equivalence(self):
        program = [
            VariableDeclaration('int', 'counter', Integer(0)),
            WhileStatement(BinaryOperation(Variable('counter'), '<', Integer(3)), [
                Assignment('counter', BinaryOperation(Variable('counter'), '+', Integer(1))),
            ]),
            IfStatement(Boolean(True), [Assignment('counter', BinaryOperation(Variable('counter'), '+', Integer(39)))], []),
        ]
        expected = QRVMCompiler().compile(program)
        actual = compile_ir_statements(tuple(lower_statement(x) for x in program))
        self.assertEqual(actual['instructions'], expected['instructions'])

    def test_unsupported_ir_is_explicit(self):
        from qrvm.ir_bridge import to_ast
        from frontend.quar.ir.model import UnsupportedIRNode
        with self.assertRaises(UnsupportedIRNode):
            to_ast(object())
