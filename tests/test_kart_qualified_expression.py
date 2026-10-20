"""Chapter 14.21: qualified calls inside expressions."""
import unittest

from frontend.quar.ast_nodes import FunctionCall, VariableDeclaration, ReturnStatement
from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser


class KartQualifiedExpressionTests(unittest.TestCase):
    def parse(self, source):
        return Parser(Lexer(source).tokenize()).parse()

    def test_qualified_call_in_initializer(self):
        statements = self.parse("int result = lib.math.add(20, 22);")
        self.assertIsInstance(statements[0], VariableDeclaration)
        self.assertIsInstance(statements[0].value, FunctionCall)
        self.assertEqual(statements[0].value.name, "lib.math.add")

    def test_qualified_call_in_return(self):
        statements = self.parse("int answer() { return lib.math.add(20, 22); }")
        value = statements[0].body[0].value
        self.assertIsInstance(value, FunctionCall)
        self.assertEqual(value.name, "lib.math.add")

    def test_simple_call_preserved(self):
        statements = self.parse("int result = add(20, 22);")
        self.assertEqual(statements[0].value.name, "add")
