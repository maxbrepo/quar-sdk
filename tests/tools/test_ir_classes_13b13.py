"""Class metadata and QRVM compatibility through Quar IR."""
import unittest
from frontend.quar.ast_nodes import (ClassDefinition, ClassField, ClassConstructor,
    ClassMethod, FunctionDefinition, FunctionParameter, Assignment, Integer,
    ObjectDeclaration, VariableDeclaration, MemberAccess, MemberAssignment)
from frontend.quar.ir.builder import lower_statement
from frontend.quar.ir.model import IRClassDefinition
from qrvm.ir_bridge import to_ast, compile_ir_statements
from qrvm.compiler import QRVMCompiler
from qrvm.vm import QRVM


class IRClassTests(unittest.TestCase):
    def test_class_roundtrip_preserves_visibility_and_methods(self):
        original = ClassDefinition('Counter', [ClassField('int', 'value', 'private')],
            ClassConstructor([FunctionParameter('int', 'start')],
                [Assignment('value', Integer(3))], 'public'),
            [ClassMethod(FunctionDefinition('int', 'read', [],
                [VariableDeclaration('int', 'tmp', Integer(7))]), 'public')])
        lowered = lower_statement(original)
        self.assertIsInstance(lowered, IRClassDefinition)
        self.assertEqual(to_ast(lowered), original)

    def test_class_object_executes_equivalently(self):
        program = [ClassDefinition('Box', [ClassField('int', 'value', 'public')], None, []),
                   ObjectDeclaration('Box', 'box', [Integer(0)]),
                   MemberAssignment('box', 'value', Integer(42)),
                   VariableDeclaration('int', 'result', MemberAccess('box', 'value'))]
        direct = QRVMCompiler().compile(program)
        via_ir = compile_ir_statements([lower_statement(n) for n in program])
        self.assertEqual(direct['instructions'], via_ir['instructions'])
        a, b = QRVM(), QRVM()
        a.run(direct)
        b.run(via_ir)
        self.assertEqual(a.variables, b.variables)
        self.assertEqual(b.variables['result'], 42)


if __name__ == '__main__':
    unittest.main()
