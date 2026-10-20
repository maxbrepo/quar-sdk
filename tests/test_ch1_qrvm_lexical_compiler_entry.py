"""Tests for the opt-in QRVM lexical compiler entry point."""
import unittest

from frontend.quar.ast_nodes import Assignment, Boolean, IfStatement, Integer, VariableDeclaration
from qrvm.compiler import QRVMCompiler
from qrvm.instructions import OpCode


class LexicalCompilerEntryTests(unittest.TestCase):
    def test_opt_in_shadowing_and_original_ast_unchanged(self):
        source = [VariableDeclaration('int', 'x', Integer(1)),
                  IfStatement(Boolean(True), [VariableDeclaration('int', 'x', Integer(2)),
                                              Assignment('x', Integer(3))], []),
                  Assignment('x', Integer(4))]
        result = QRVMCompiler().compile(source, lexical=True)
        stores = [operand for op, operand in result['instructions'] if op == OpCode.STORE]
        self.assertEqual(len(stores), 4)
        self.assertEqual(stores[0], stores[3])
        self.assertEqual(stores[1], stores[2])
        self.assertNotEqual(stores[0], stores[1])
        self.assertEqual(source[0].name, 'x')
        self.assertEqual(source[1].then_body[0].name, 'x')

    def test_opt_in_inference_preserves_outer_assignment(self):
        source = [Assignment('x', Integer(1)),
                  IfStatement(Boolean(True), [Assignment('x', Integer(2))], []),
                  Assignment('x', Integer(3))]
        result = QRVMCompiler().compile(source, lexical=True, allow_inference=True)
        stores = [operand for op, operand in result['instructions'] if op == OpCode.STORE]
        self.assertEqual(stores, [stores[0]] * 3)

    def test_unsupported_node_rejected_only_in_opt_in_mode(self):
        with self.assertRaises(NotImplementedError):
            QRVMCompiler().compile([object()], lexical=True)

    def test_undeclared_assignment_rejected_without_inference(self):
        with self.assertRaises(NameError):
            QRVMCompiler().compile([Assignment('x', Integer(1))], lexical=True)


if __name__ == '__main__':
    unittest.main()
