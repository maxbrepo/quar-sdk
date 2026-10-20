"""Lexical lowering contracts for constants and counter loops."""
import unittest

from frontend.quar.ast_nodes import (
    Assignment, BinaryOperation, ConstantDeclaration, ForStatement,
    Integer, Variable, VariableDeclaration,
)
from frontend.quar.lexical_bytecode import LexicalBytecodeLowerer
from qrvm.compiler import QRVMCompiler


class LexicalConstantsForTests(unittest.TestCase):
    def test_constant_shadows_outer_binding(self):
        source = [
            VariableDeclaration('int', 'x', Integer(1)),
            ForStatement('x', Integer(1), BinaryOperation(Variable('x'), '<', Integer(2)),
                         [ConstantDeclaration('int', 'y', Variable('x'))]),
        ]
        lowered = LexicalBytecodeLowerer().lower(source)
        self.assertEqual(lowered[1].body[0].value.name, lowered[0].name)
        self.assertNotEqual(lowered[1].body[0].name, lowered[0].name)
        QRVMCompiler().compile(lowered)

    def test_for_counter_reuses_outer_binding(self):
        source = [VariableDeclaration('int', 'i', Integer(0)),
                  ForStatement('i', Integer(0), BinaryOperation(Variable('i'), '<', Integer(2)),
                               [VariableDeclaration('int', 'i', Integer(10)),
                                Assignment('i', Integer(11))])]
        lowered = LexicalBytecodeLowerer().lower(source)
        self.assertEqual(lowered[1].counter_name, lowered[0].name)
        self.assertEqual(lowered[1].comparison.left.name, lowered[0].name)
        self.assertEqual(lowered[1].body[1].name, lowered[1].body[0].name)
        self.assertNotEqual(lowered[1].body[0].name, lowered[0].name)
        QRVMCompiler().compile(lowered)

    def test_for_counter_inference(self):
        source = [ForStatement('i', Integer(0),
                               BinaryOperation(Variable('i'), '<', Integer(2)), [])]
        lowered = LexicalBytecodeLowerer(allow_inference=True).lower(source)
        self.assertEqual(lowered[0].counter_name, lowered[0].comparison.left.name)
        # A for header introduces an integer counter even in typed mode.
        typed = LexicalBytecodeLowerer().lower(source)
        self.assertEqual(typed[0].counter_name, typed[0].comparison.left.name)
        # This exception does not permit arbitrary inferred assignments.
        with self.assertRaises(NameError):
            LexicalBytecodeLowerer().lower([Assignment('missing', Integer(1))])

    def test_loop_local_constant_does_not_escape(self):
        source = [VariableDeclaration('int', 'i', Integer(0)),
                  ForStatement('i', Integer(0), BinaryOperation(Variable('i'), '<', Integer(1)),
                               [ConstantDeclaration('int', 'local', Integer(4))]),
                  Assignment('i', Variable('local'))]
        with self.assertRaises(NameError):
            LexicalBytecodeLowerer().lower(source)


if __name__ == '__main__':
    unittest.main()
