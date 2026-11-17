"""Chapter 5.39: variadic syntax only, not runtime support."""
import unittest
from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from frontend.quar.errors import ParserError


def parse(source):
    return Parser(Lexer(source).tokenize()).parse()


class VariadicParserTests(unittest.TestCase):
    def test_variadic_final_parameter(self):
        node = parse('int sum(int first, int... rest) { return first; }')[0]
        self.assertFalse(node.parameters[0].is_variadic)
        self.assertTrue(node.parameters[1].is_variadic)
        self.assertEqual(node.parameters[1].var_type, 'int')

    def test_only_variadic_parameter(self):
        node = parse('void log(string... items) { return; }')[0]
        self.assertTrue(node.parameters[0].is_variadic)

    def test_non_final_variadic_rejected(self):
        with self.assertRaises(ParserError):
            parse('int bad(int... items, int x) { return x; }')

    def test_multiple_variadics_rejected(self):
        with self.assertRaises(ParserError):
            parse('void bad(int... a, int... b) { return; }')

    def test_variadic_default_rejected(self):
        with self.assertRaises(ParserError):
            parse('void bad(int... items = 2) { return; }')

    def test_existing_parameters_unchanged(self):
        node = parse('int id(int x) { return x; }')[0]
        self.assertFalse(node.parameters[0].is_variadic)
