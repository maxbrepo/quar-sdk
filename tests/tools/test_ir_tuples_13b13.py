"""Differential QRVM tests for tuple lowering and unpacking."""
import unittest
from frontend.quar.ast_nodes import (Integer, TupleLiteral, TupleDeclaration,
    DestructuringDeclaration, TypeAlias)
from frontend.quar.ir.builder import lower_statement
from frontend.quar.ir.model import IRTupleDeclare, IRDestructure, IRTypeAlias
from qrvm.compiler import QRVMCompiler
from qrvm.ir_bridge import compile_ir_statements
from qrvm.vm import QRVM


class IRTupleTests(unittest.TestCase):
    def compare(self, program):
        ir = tuple(lower_statement(node) for node in program)
        direct = QRVMCompiler().compile(program)
        bridged = compile_ir_statements(ir)
        self.assertEqual(direct['instructions'], bridged['instructions'])
        vm_direct, vm_ir = QRVM(), QRVM()
        vm_direct.run(direct)
        vm_ir.run(bridged)
        self.assertEqual(vm_direct.variables, vm_ir.variables)
        return ir, vm_ir

    def test_tuple_creation(self):
        ir, vm = self.compare([TupleDeclaration('pair', TupleLiteral([Integer(3), Integer(8)]))])
        self.assertIsInstance(ir[0], IRTupleDeclare)
        self.assertEqual(vm.variables['pair'], (3, 8))

    def test_tuple_unpack(self):
        ir, vm = self.compare([DestructuringDeclaration([('int', 'left'), ('int', 'right')],
                                   TupleLiteral([Integer(5), Integer(12)]))])
        self.assertIsInstance(ir[0], IRDestructure)
        self.assertEqual(vm.variables['left'], 5)
        self.assertEqual(vm.variables['right'], 12)

    def test_type_alias_metadata(self):
        ir, _ = self.compare([TypeAlias('Index', 'int')])
        self.assertIsInstance(ir[0], IRTypeAlias)


if __name__ == '__main__':
    unittest.main()
