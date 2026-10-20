"""Differential IR tests for switch and match using the existing QRVM."""
import unittest
from frontend.quar.ast_nodes import (Integer, Variable, VariableDeclaration,
    SwitchCase, SwitchStatement, MatchArm, MatchStatement, FunctionCall)
from frontend.quar.ir.builder import lower_statement
from frontend.quar.ir.model import IRSwitch, IRMatch
from qrvm.ir_bridge import compile_ir_statements
from qrvm.compiler import QRVMCompiler
from qrvm.vm import QRVM

class SwitchMatchIRTests(unittest.TestCase):
    def compare(self, program, expected):
        direct = QRVMCompiler().compile(program)
        lowered = tuple(lower_statement(node) for node in program)
        via_ir = compile_ir_statements(lowered)
        self.assertEqual(direct['instructions'], via_ir['instructions'])
        vm1, vm2 = QRVM(), QRVM()
        vm1.run(direct)
        vm2.run(via_ir)
        self.assertEqual(vm1.variables, vm2.variables)
        self.assertEqual(vm2.variables['result'], expected)

    def test_switch_case(self):
        self.compare([VariableDeclaration('int', 'result', Integer(0)),
            SwitchStatement(Integer(2), [SwitchCase(Integer(1), [VariableDeclaration('int', 'result', Integer(10))]),
                SwitchCase(Integer(2), [VariableDeclaration('int', 'result', Integer(42))])],
                [VariableDeclaration('int', 'result', Integer(99))])], 42)

    def test_switch_default(self):
        self.compare([VariableDeclaration('int', 'result', Integer(0)),
            SwitchStatement(Integer(5), [SwitchCase(Integer(1), [])],
                [VariableDeclaration('int', 'result', Integer(7))])], 7)

    def test_match_roundtrip(self):
        node = MatchStatement(Variable('item'),
            [MatchArm('Some', ['value'], [FunctionCall('use', [Variable('value')])])], [])
        ir = lower_statement(node)
        self.assertIsInstance(ir, IRMatch)
        from qrvm.ir_bridge import to_ast
        self.assertEqual(to_ast(ir), node)

if __name__ == '__main__':
    unittest.main()
