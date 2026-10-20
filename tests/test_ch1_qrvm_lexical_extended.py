"""Regression tests for opt-in lexical lowering of loops and functions."""
import unittest

from frontend.quar.ast_nodes import (
    Assignment, Boolean, FunctionCall, FunctionDefinition, FunctionParameter,
    Integer, ReturnStatement, Variable, VariableDeclaration, WhileStatement,
)
from frontend.quar.lexical_bytecode import LexicalBytecodeLowerer
from qrvm.compiler import QRVMCompiler
from qrvm.instructions import OpCode


class LexicalExtendedTests(unittest.TestCase):
    def test_while_body_shadows_and_condition_uses_outer(self):
        source = [VariableDeclaration('int', 'x', Integer(1)),
                  WhileStatement(Variable('x'), [VariableDeclaration('int', 'x', Integer(2)),
                                                 Assignment('x', Integer(3))]),
                  Assignment('x', Integer(4))]
        lowered = LexicalBytecodeLowerer().lower(source)
        outer = lowered[0].name
        inner = lowered[1].body[0].name
        self.assertEqual(lowered[1].condition.name, outer)
        self.assertEqual(lowered[1].body[1].name, inner)
        self.assertEqual(lowered[2].name, outer)
        self.assertNotEqual(outer, inner)
        compiled = QRVMCompiler().compile(lowered)
        self.assertTrue(any(op == OpCode.STORE and value == inner for op, value in compiled['instructions']))

    def test_function_parameter_isolated_and_return_resolved(self):
        source = [FunctionDefinition('int', 'first', [FunctionParameter('int', 'x')],
                                     [ReturnStatement(Variable('x'))]),
                  FunctionDefinition('int', 'second', [FunctionParameter('int', 'x')],
                                     [ReturnStatement(Variable('x'))])]
        lowered = LexicalBytecodeLowerer().lower(source)
        first, second = lowered
        self.assertNotEqual(first.parameters[0].name, second.parameters[0].name)
        self.assertEqual(first.body[0].value.name, first.parameters[0].name)
        self.assertEqual(second.body[0].value.name, second.parameters[0].name)
        self.assertEqual(source[0].parameters[0].name, 'x')

    def test_function_cannot_see_unrelated_function_locals(self):
        source = [FunctionDefinition('int', 'first', [FunctionParameter('int', 'x')],
                                     [ReturnStatement(Variable('x'))]),
                  FunctionDefinition('int', 'second', [], [ReturnStatement(Variable('x'))])]
        with self.assertRaises(NameError):
            LexicalBytecodeLowerer().lower(source)

    def test_function_call_argument_uses_visible_binding(self):
        source = [VariableDeclaration('int', 'x', Integer(1)), FunctionCall('print', [Variable('x')])]
        lowered = LexicalBytecodeLowerer().lower(source)
        self.assertEqual(lowered[1].arguments[0].name, lowered[0].name)
        self.assertEqual(lowered[1].name, 'print')


if __name__ == '__main__':
    unittest.main()
