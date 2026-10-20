"""Differential tests for struct/record lowering and QRVM execution."""
import unittest
from frontend.quar.ast_nodes import (TypeField, StructDefinition, RecordDefinition, ObjectDeclaration,
    MemberAccess, MemberAssignment, Integer, VariableDeclaration)
from frontend.quar.ir.builder import lower_statement
from qrvm.ir_bridge import compile_ir_statements
from qrvm.compiler import QRVMCompiler
from qrvm.vm import QRVM

class IRStructureTests(unittest.TestCase):
    def compare(self, program, expected):
        direct = QRVMCompiler().compile(program)
        through_ir = compile_ir_statements(tuple(lower_statement(n) for n in program))
        self.assertEqual(direct['instructions'], through_ir['instructions'])
        a, b = QRVM(), QRVM()
        a.run(direct)
        b.run(through_ir)
        self.assertEqual(a.variables, b.variables)
        self.assertEqual(b.variables['result'], expected)

    def test_struct_member_read(self):
        self.compare([StructDefinition('Point', [TypeField('int', 'x')]),
                      ObjectDeclaration('Point', 'point', [Integer(0)]),
                      MemberAssignment('point', 'x', Integer(42)),
                      VariableDeclaration('int', 'result', MemberAccess('point', 'x'))], 42)

    def test_record_member_write(self):
        self.compare([RecordDefinition('Counter', [TypeField('int', 'value')]),
                      ObjectDeclaration('Counter', 'counter', [Integer(0)]),
                      MemberAssignment('counter', 'value', Integer(7)),
                      VariableDeclaration('int', 'result', MemberAccess('counter', 'value'))], 7)

if __name__ == '__main__':
    unittest.main()
