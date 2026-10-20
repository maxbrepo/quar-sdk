"""Chapter 15: regression tests for existing initialization guarantees."""

import unittest

from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from frontend.quar.semantic import SemanticAnalyzer
from frontend.quar.errors import ParserError, SemanticError
from frontend.quar.ast_nodes import VariableDeclaration, Integer, Boolean, String


def analyze(source: str):
    """Parse and validate source; return the checked AST."""
    program = Parser(Lexer(source).tokenize()).parse()
    SemanticAnalyzer().analyze(program)
    return program


class MemoryInitializationBaselineTests(unittest.TestCase):
    def test_integer_has_defined_default(self):
        program = analyze('int value; print(value);')
        self.assertIsInstance(program[0], VariableDeclaration)
        self.assertIsInstance(program[0].value, Integer)
        self.assertEqual(program[0].value.value, 0)

    def test_boolean_has_defined_default(self):
        program = analyze('bool ready; print(ready);')
        self.assertIsInstance(program[0].value, Boolean)
        self.assertFalse(program[0].value.value)

    def test_string_has_defined_default(self):
        program = analyze('string label; print(label);')
        self.assertIsInstance(program[0].value, String)
        self.assertEqual(program[0].value.value, '')

    def test_read_of_undeclared_variable_rejected(self):
        with self.assertRaises(SemanticError):
            analyze('print(missing);')

    def test_unsupported_implicit_default_rejected(self):
        with self.assertRaises(ParserError):
            analyze('unknown_type value;')


if __name__ == '__main__':
    unittest.main()
