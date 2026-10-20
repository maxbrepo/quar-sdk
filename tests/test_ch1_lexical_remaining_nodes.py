"""Lexical identity checks for compound statements and expressions."""
import unittest

from frontend.quar.ast_nodes import (
    Assignment, DestructuringDeclaration, Integer, MatchArm, MatchStatement,
    TryCatchStatement, TupleDeclaration, TupleLiteral, Variable,
    VariableDeclaration, VariantConstructor, WithFileStatement,
)
from frontend.quar.lexical_bytecode import LexicalBytecodeLowerer


class RemainingLexicalNodesTests(unittest.TestCase):
    def lower(self, program):
        return LexicalBytecodeLowerer().lower(program)

    def test_tuple_and_destructuring(self):
        source = [
            VariableDeclaration('int', 'x', Integer(1)),
            TupleDeclaration('pair', TupleLiteral([Variable('x'), Integer(2)])),
            DestructuringDeclaration([('int', 'a'), ('int', 'y')], TupleLiteral([Integer(3), Variable('x')])),
        ]
        lowered = self.lower(source)
        self.assertEqual(lowered[1].value.values[0].name, lowered[0].name)
        self.assertEqual(lowered[2].value.values[1].name, lowered[0].name)
        self.assertEqual(lowered[2].bindings[0][0], 'int')
        self.assertNotEqual(lowered[2].bindings[0][1], lowered[0].name)
        self.assertEqual(source[0].name, 'x')

    def test_match_arm_bindings_are_isolated(self):
        source = [VariableDeclaration('int', 'x', Integer(1)), MatchStatement(
            VariantConstructor('Result', 'Ok', [Variable('x')]),
            [MatchArm('Ok', ['x'], [Assignment('x', Integer(4))])],
            [Assignment('x', Integer(5))],
        )]
        lowered = self.lower(source)
        outer = lowered[0].name
        arm = lowered[1].arms[0]
        self.assertNotEqual(arm.bindings[0], outer)
        self.assertEqual(arm.body[0].name, arm.bindings[0])
        self.assertEqual(lowered[1].default_body[0].name, outer)

    def test_file_binding_is_scoped(self):
        source = [VariableDeclaration('int', 'f', Integer(1)), WithFileStatement(
            Integer(2), Integer(3), 'f', [Assignment('f', Integer(4))]),
            Assignment('f', Integer(5))]
        lowered = self.lower(source)
        self.assertNotEqual(lowered[1].name, lowered[0].name)
        self.assertEqual(lowered[1].body[0].name, lowered[1].name)
        self.assertEqual(lowered[2].name, lowered[0].name)

    def test_catch_binding_is_scoped(self):
        source = [VariableDeclaration('int', 'err', Integer(1)), TryCatchStatement(
            [Assignment('err', Integer(2))], 'err', [Assignment('err', Integer(3))]),
            Assignment('err', Integer(4))]
        lowered = self.lower(source)
        self.assertEqual(lowered[1].try_body[0].name, lowered[0].name)
        self.assertNotEqual(lowered[1].catch_body[0].name, lowered[0].name)
        self.assertEqual(lowered[2].name, lowered[0].name)

    def test_match_binding_does_not_leak(self):
        source = [MatchStatement(Integer(1), [MatchArm('Ok', ['temporary'], [])], []),
                  Assignment('temporary', Integer(2))]
        with self.assertRaises(NameError):
            self.lower(source)


if __name__ == '__main__':
    unittest.main()
