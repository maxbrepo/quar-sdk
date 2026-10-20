"""Chapter 15.15: optional assignment lowering and non-nesting."""
import unittest
from frontend.quar.ast_nodes import Assignment, Integer, Variable, VariableDeclaration
from qrvm.compiler import QRVMCompiler
from qrvm.instructions import OpCode
from qrvm.vm import QRVM


class OptionalAssignmentTests(unittest.TestCase):
    def run_program(self, statements, name):
        compiler = QRVMCompiler()
        code = compiler.compile(statements)
        vm = QRVM()
        vm.run(code)
        return vm.variables[name]

    def test_ordinary_value_is_wrapped_on_assignment(self):
        value = self.run_program([VariableDeclaration('int?', 'x', None), Assignment('x', Integer(12))], 'x')
        self.assertTrue(value.present)
        self.assertEqual(value.value, 12)

    def test_optional_variable_assignment_is_not_nested(self):
        value = self.run_program([VariableDeclaration('int?', 'x', Integer(12)), VariableDeclaration('int?', 'y', None), Assignment('y', Variable('x'))], 'y')
        self.assertTrue(value.present)
        self.assertEqual(value.value, 12)
        self.assertFalse(hasattr(value.value, 'present'))

    def test_optional_initialization_from_optional_is_not_nested(self):
        value = self.run_program([VariableDeclaration('int?', 'x', Integer(8)), VariableDeclaration('int?', 'y', Variable('x'))], 'y')
        self.assertEqual(value.value, 8)
        self.assertFalse(hasattr(value.value, 'present'))

    def test_absence_can_be_assigned(self):
        value = self.run_program([VariableDeclaration('int?', 'x', Integer(8)), Assignment('x', None)], 'x')
        self.assertFalse(value.present)

    def test_non_optional_assignment_unchanged(self):
        compiler = QRVMCompiler()
        compiler.compile_statement(VariableDeclaration('int', 'x', Integer(1)))
        code = compiler.compile_statement(Assignment('x', Integer(2)))
        self.assertEqual([op for op, _ in code], [OpCode.PUSH_INT, OpCode.STORE])

    def test_compile_resets_optional_tracking(self):
        compiler = QRVMCompiler()
        compiler.compile([VariableDeclaration('int?', 'x', None)])
        code = compiler.compile([Assignment('x', Integer(2))])['instructions']
        self.assertNotIn(OpCode.OPTIONAL_SOME, [op for op, _ in code])

if __name__ == '__main__':
    unittest.main()
