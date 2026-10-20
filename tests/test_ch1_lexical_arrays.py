"""Array binding contracts for the opt-in lexical lowering path."""
import unittest

from frontend.quar.ast_nodes import (
    ArrayAccess, ArrayAssignment, ArrayDeclaration, Assignment,
    IfStatement, Integer, Variable, VariableDeclaration,
)
from frontend.quar.lexical_bytecode import LexicalBytecodeLowerer
from qrvm.compiler import QRVMCompiler


class LexicalArrayTests(unittest.TestCase):
    def test_array_declaration_access_and_assignment_share_identity(self):
        source = [ArrayDeclaration('int', 'items', 2, [Integer(1), Integer(2)]),
                  ArrayAssignment('items', Integer(0), Integer(9)),
                  VariableDeclaration('int', 'value', ArrayAccess('items', Integer(0)))]
        lowered = LexicalBytecodeLowerer().lower(source)
        self.assertEqual(lowered[0].name, lowered[1].name)
        self.assertEqual(lowered[0].name, lowered[2].value.name)
        self.assertEqual(source[0].name, 'items')
        QRVMCompiler().compile(lowered)

    def test_array_shadowing_inside_block(self):
        source = [ArrayDeclaration('int', 'items', 1, [Integer(1)]),
                  IfStatement(Integer(1), [
                      ArrayDeclaration('int', 'items', 1, [Integer(3)]),
                      ArrayAssignment('items', Integer(0), Integer(4))], []),
                  ArrayAssignment('items', Integer(0), Integer(2))]
        lowered = LexicalBytecodeLowerer().lower(source)
        self.assertNotEqual(lowered[0].name, lowered[1].then_body[0].name)
        self.assertEqual(lowered[1].then_body[0].name, lowered[1].then_body[1].name)
        self.assertEqual(lowered[0].name, lowered[2].name)

    def test_array_indices_and_initializers_resolve_variables(self):
        source = [VariableDeclaration('int', 'i', Integer(0)),
                  ArrayDeclaration('int', 'items', 2, [Variable('i'), Integer(4)]),
                  ArrayAssignment('items', Variable('i'), ArrayAccess('items', Variable('i')))]
        lowered = LexicalBytecodeLowerer().lower(source)
        identity = lowered[0].name
        self.assertEqual(lowered[1].initial_values[0].name, identity)
        self.assertEqual(lowered[2].index.name, identity)
        self.assertEqual(lowered[2].value.index.name, identity)

    def test_array_block_scope_does_not_escape(self):
        source = [IfStatement(Integer(1), [ArrayDeclaration('int', 'local', 1)], []),
                  ArrayAssignment('local', Integer(0), Integer(1))]
        with self.assertRaises(NameError):
            LexicalBytecodeLowerer().lower(source)

    def test_duplicate_array_declaration_rejected(self):
        source = [ArrayDeclaration('int', 'items', 1), ArrayDeclaration('int', 'items', 2)]
        with self.assertRaises(ValueError):
            LexicalBytecodeLowerer().lower(source)


if __name__ == '__main__':
    unittest.main()
