"""Experimental parser coverage for function references (not runtime support)."""
import unittest

from frontend.quar.ast_nodes import FunctionCall, FunctionReference, Integer
from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from frontend.quar.errors import ParserError


class FunctionReferenceParserTests(unittest.TestCase):
    def parse(self, source):
        """Return parsed statements for a complete source string."""
        return Parser(Lexer(source).tokenize()).parse()

    def test_reference_as_argument(self):
        statement = self.parse('print(&add);')[0]
        self.assertEqual(statement, FunctionCall('print', [FunctionReference('add')]))

    def test_reference_is_not_call(self):
        reference = self.parse('print(&add);')[0].arguments[0]
        self.assertNotIsInstance(reference, FunctionCall)

    def test_direct_call_unchanged(self):
        self.assertEqual(self.parse('print(1);')[0], FunctionCall('print', [Integer(1)]))

    def test_reference_requires_identifier(self):
        with self.assertRaises(ParserError):
            self.parse('print(&1);')


if __name__ == '__main__':
    unittest.main()
