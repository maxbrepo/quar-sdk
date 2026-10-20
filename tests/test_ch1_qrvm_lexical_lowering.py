"""Opt-in QRVM lexical lowering tests."""
import unittest

from frontend.quar.ast_nodes import (
    Assignment, Boolean, IfStatement, Integer, Variable, VariableDeclaration,
)
from frontend.quar.lexical_bytecode import LexicalBytecodeLowerer
from qrvm.compiler import QRVMCompiler
from qrvm.instructions import OpCode


class LexicalBytecodeTests(unittest.TestCase):
    def test_shadowed_storage_and_outer_assignment(self):
        source = [
            VariableDeclaration("int", "x", Integer(1)),
            IfStatement(Boolean(True), [
                VariableDeclaration("int", "x", Integer(2)),
                Assignment("x", Integer(3)),
            ], []),
            Assignment("x", Integer(4)),
        ]
        lowered = LexicalBytecodeLowerer().lower(source)
        outer = lowered[0].name
        inner = lowered[1].then_body[0].name
        self.assertNotEqual(outer, inner)
        self.assertEqual(lowered[1].then_body[1].name, inner)
        self.assertEqual(lowered[2].name, outer)
        self.assertEqual(source[0].name, "x")
        compiled = QRVMCompiler().compile(lowered)
        stores = [value for opcode, value in compiled["instructions"] if opcode == OpCode.STORE]
        self.assertEqual(stores, [outer, inner, inner, outer])

    def test_inferred_assignment_targets_outer_storage(self):
        source = [Assignment("x", Integer(1)), IfStatement(Boolean(True), [
            Assignment("x", Integer(2)), Assignment("y", Integer(3)),
        ], []), Assignment("x", Integer(4))]
        lowered = LexicalBytecodeLowerer(allow_inference=True).lower(source)
        self.assertEqual(lowered[0].name, lowered[1].then_body[0].name)
        self.assertEqual(lowered[0].name, lowered[2].name)
        self.assertNotEqual(lowered[0].name, lowered[1].then_body[1].name)

    def test_branch_binding_is_not_visible_after_branch(self):
        source = [IfStatement(Boolean(True), [VariableDeclaration("int", "local", Integer(1))], []),
                  Assignment("local", Integer(2))]
        with self.assertRaises(NameError):
            LexicalBytecodeLowerer().lower(source)
        lowered = LexicalBytecodeLowerer(allow_inference=True).lower(source)
        self.assertNotEqual(lowered[0].then_body[0].name, lowered[1].name)

    def test_unhandled_nodes_fail_closed(self):
        with self.assertRaises(NotImplementedError):
            LexicalBytecodeLowerer().lower([object()])
