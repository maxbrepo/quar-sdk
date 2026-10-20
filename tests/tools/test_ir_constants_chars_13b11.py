"""Verify constant and character lowering against the existing QRVM pipeline."""
import unittest

from frontend.quar.ast_nodes import Char, ConstantDeclaration, Integer, Variable, VariableDeclaration
from frontend.quar.ir.builder import lower_statement
from frontend.quar.ir.model import IRChar, IRConstant
from qrvm.compiler import QRVMCompiler
from qrvm.ir_bridge import compile_ir_statements
from qrvm.vm import QRVM


class IRConstantsAndCharsTests(unittest.TestCase):
    def test_character_expression(self):
        program = [VariableDeclaration('char', 'letter', Char('Q'))]
        ir = tuple(map(lower_statement, program))
        self.assertIsInstance(ir[0].value, IRChar)
        self.compare_execution(program, ir)

    def test_constant_declaration(self):
        program = [ConstantDeclaration('int', 'limit', Integer(42)),
                   VariableDeclaration('int', 'result', Variable('limit'))]
        ir = tuple(map(lower_statement, program))
        self.assertIsInstance(ir[0], IRConstant)
        self.compare_execution(program, ir)

    def compare_execution(self, program, ir):
        direct = QRVMCompiler().compile(program)
        bridged = compile_ir_statements(ir)
        self.assertEqual(direct['instructions'], bridged['instructions'])
        vm_direct, vm_ir = QRVM(), QRVM()
        vm_direct.run(direct)
        vm_ir.run(bridged)
        self.assertEqual(vm_direct.variables, vm_ir.variables)


if __name__ == '__main__':
    unittest.main()
