"""Lexical identity across switch cases and additional control-flow statements."""
import unittest

from frontend.quar.ast_nodes import (
    Assignment, BreakStatement, ContinueStatement, DoWhileStatement,
    IfStatement, Integer, LoopStatement, SwitchCase, SwitchStatement,
    ThrowStatement, TypeAlias, Variable, VariableDeclaration,
)
from frontend.quar.lexical_bytecode import LexicalBytecodeLowerer


class LexicalControlFlowTests(unittest.TestCase):
    def test_switch_cases_are_isolated(self):
        source = [VariableDeclaration('int', 'x', Integer(1)),
                  SwitchStatement(Variable('x'), [
                      SwitchCase(Integer(1), [VariableDeclaration('int', 'x', Integer(2)),
                                                      Assignment('x', Integer(3)), BreakStatement()]),
                      SwitchCase(Integer(2), [VariableDeclaration('int', 'x', Integer(4))])],
                      [Assignment('x', Integer(5))]),
                  Assignment('x', Integer(6))]
        result = LexicalBytecodeLowerer().lower(source)
        outer = result[0].name
        first = result[1].cases[0].body[0].name
        second = result[1].cases[1].body[0].name
        self.assertEqual(result[1].expression.name, outer)
        self.assertEqual(result[1].cases[0].body[1].name, first)
        self.assertEqual(result[1].default_body[0].name, outer)
        self.assertEqual(result[2].name, outer)
        self.assertEqual(len({outer, first, second}), 3)
        self.assertEqual(source[0].name, 'x')

    def test_switch_case_does_not_leak(self):
        source = [SwitchStatement(Integer(1), [SwitchCase(Integer(1), [
            VariableDeclaration('int', 'local', Integer(2))])], []),
            Assignment('local', Integer(3))]
        with self.assertRaises(NameError):
            LexicalBytecodeLowerer().lower(source)

    def test_do_while_and_loop_scope(self):
        source = [VariableDeclaration('int', 'x', Integer(1)),
                  DoWhileStatement([VariableDeclaration('int', 'x', Integer(2)),
                                    ContinueStatement()], Variable('x')),
                  LoopStatement([VariableDeclaration('int', 'x', Integer(3)),
                                 BreakStatement()]), Assignment('x', Integer(4))]
        result = LexicalBytecodeLowerer().lower(source)
        outer = result[0].name
        self.assertNotEqual(result[1].body[0].name, outer)
        self.assertNotEqual(result[2].body[0].name, outer)
        self.assertEqual(result[1].condition.name, outer)
        self.assertEqual(result[3].name, outer)

    def test_throw_and_type_alias_preserve_names(self):
        source = [TypeAlias('Count', 'int'), VariableDeclaration('int', 'x', Integer(3)),
                  IfStatement(Integer(1), [ThrowStatement(Variable('x'))], [])]
        result = LexicalBytecodeLowerer().lower(source)
        self.assertEqual(result[0].name, 'Count')
        self.assertEqual(result[2].then_body[0].message.name, result[1].name)


if __name__ == '__main__':
    unittest.main()
