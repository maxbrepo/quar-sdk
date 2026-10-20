"""Array lowering parity against the existing bytecode compiler and VM."""
import unittest
from frontend.quar.ast_nodes import ArrayDeclaration, ArrayAccess, ArrayAssignment, Integer, VariableDeclaration
from frontend.quar.ir.builder import lower_statement
from qrvm.compiler import QRVMCompiler
from qrvm.ir_bridge import compile_ir_statements
from qrvm.vm import QRVM

class IRArrayTests(unittest.TestCase):
    def compare(self, program, name, expected):
        direct = QRVMCompiler().compile(program)
        via_ir = compile_ir_statements(tuple(lower_statement(node) for node in program))
        self.assertEqual(direct['instructions'], via_ir['instructions'])
        original, converted = QRVM(), QRVM()
        original.run(direct)
        converted.run(via_ir)
        self.assertEqual(original.variables, converted.variables)
        self.assertEqual(converted.variables[name], expected)

    def test_array_initialization_and_read(self):
        self.compare([ArrayDeclaration('int', 'values', 3, [Integer(2), Integer(5), Integer(9)]),
                      VariableDeclaration('int', 'result', ArrayAccess('values', Integer(1)))], 'result', 5)

    def test_array_write_then_read(self):
        self.compare([ArrayDeclaration('int', 'values', 2),
                      ArrayAssignment('values', Integer(1), Integer(42)),
                      VariableDeclaration('int', 'result', ArrayAccess('values', Integer(1)))], 'result', 42)

if __name__ == '__main__':
    unittest.main()
