"""Executable guard against confusing lexical lowering with C backend support."""
import unittest

from backend.c.codegen import CCodeGenerator
from frontend.quar.ast_nodes import (
    ArrayDeclaration, BinaryOperation, ForStatement, Integer, SwitchStatement, Variable,
    TupleDeclaration, TupleLiteral, VariableDeclaration, WhileStatement,
)
from frontend.quar.lexical_bytecode import LexicalBytecodeLowerer


class BackendCoverageContractTests(unittest.TestCase):
    def test_c_backend_generates_supported_while(self):
        source = [VariableDeclaration('int', 'counter', Integer(1)),
                  WhileStatement(Integer(0), [])]
        c_source = CCodeGenerator().generate(source, lexical=True)
        self.assertIn('while (0)', c_source)

    def test_for_is_now_emitted_as_c(self):
        source = [VariableDeclaration('int', 'i', Integer(0)),
                  ForStatement('i', Integer(0),
                               BinaryOperation(Variable('i'), '<', Integer(2)), [])]
        generated = CCodeGenerator().generate(source)
        self.assertIn('for (i = 0; (i < 2); i += 1)', generated)

    def test_fixed_array_is_now_emitted_as_c(self):
        source = [ArrayDeclaration('int', 'items', 1, [Integer(1)])]
        generated = CCodeGenerator().generate(source)
        self.assertIn('int32_t items[1] = {1};', generated)

    def test_multidimensional_array_remains_unsupported(self):
        source = [ArrayDeclaration('int', 'items', 1, second_size=2)]
        with self.assertRaisesRegex(ValueError, 'one-dimensional'):
            CCodeGenerator().generate(source)

    def test_tuple_is_not_silently_emitted_as_c(self):
        source = [TupleDeclaration('pair', TupleLiteral([Integer(1), Integer(2)]))]
        with self.assertRaisesRegex(ValueError, 'Unsupported statement: TupleDeclaration'):
            CCodeGenerator().generate(source)

    def test_switch_is_not_silently_emitted_as_c(self):
        source = [SwitchStatement(Integer(1), [], [])]
        with self.assertRaisesRegex(ValueError, 'Unsupported statement: SwitchStatement'):
            CCodeGenerator().generate(source)


if __name__ == '__main__':
    unittest.main()
