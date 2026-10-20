"""Lexical identity for struct instances, without rewriting member or type names."""
import unittest

from frontend.quar.ast_nodes import (
    IfStatement, Integer, MemberAccess, MemberAssignment, ObjectDeclaration,
    StructDefinition, TypeField, VariableDeclaration,
)
from frontend.quar.lexical_bytecode import LexicalBytecodeLowerer


class LexicalObjectTests(unittest.TestCase):
    def test_instance_and_members_share_object_identity(self):
        source = [StructDefinition('Point', [TypeField('int', 'x')]),
                  ObjectDeclaration('Point', 'p', [Integer(1)]),
                  MemberAssignment('p', 'x', Integer(2)),
                  VariableDeclaration('int', 'result', MemberAccess('p', 'x'))]
        lowered = LexicalBytecodeLowerer().lower(source)
        self.assertEqual(lowered[1].name, lowered[2].object_name)
        self.assertEqual(lowered[1].name, lowered[3].value.object_name)
        self.assertEqual(lowered[1].type_name, 'Point')
        self.assertEqual(lowered[2].member_name, 'x')
        self.assertEqual(source[1].name, 'p')

    def test_inner_instance_shadows_outer_instance(self):
        source = [ObjectDeclaration('Point', 'p', []),
                  IfStatement(Integer(1), [ObjectDeclaration('Point', 'p', []),
                                            MemberAssignment('p', 'x', Integer(3))], []),
                  MemberAssignment('p', 'x', Integer(4))]
        lowered = LexicalBytecodeLowerer().lower(source)
        self.assertNotEqual(lowered[0].name, lowered[1].then_body[0].name)
        self.assertEqual(lowered[1].then_body[0].name, lowered[1].then_body[1].object_name)
        self.assertEqual(lowered[0].name, lowered[2].object_name)

    def test_out_of_scope_instance_is_rejected(self):
        source = [IfStatement(Integer(1), [ObjectDeclaration('Point', 'p', [])], []),
                  MemberAssignment('p', 'x', Integer(3))]
        with self.assertRaises(NameError):
            LexicalBytecodeLowerer().lower(source)

    def test_duplicate_instance_is_rejected(self):
        source = [ObjectDeclaration('Point', 'p', []), ObjectDeclaration('Point', 'p', [])]
        with self.assertRaises(ValueError):
            LexicalBytecodeLowerer().lower(source)


if __name__ == '__main__':
    unittest.main()
