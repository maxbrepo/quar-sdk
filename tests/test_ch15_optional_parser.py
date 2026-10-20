"""Chapter 15.9: optional type syntax in the real frontend."""
import unittest
from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from frontend.quar.tokens import TokenType
from frontend.quar.errors import ParserError


class OptionalParserTests(unittest.TestCase):
    def parse_type(self, source):
        parser = Parser(Lexer(source).tokenize())
        return parser.parse_type_name(allow_void=True)

    def test_question_token(self):
        tokens = Lexer("int?").tokenize()
        self.assertEqual([t.type for t in tokens[:2]], [TokenType.TYPE_INT, TokenType.QUESTION])

    def test_primitive_optional(self):
        self.assertEqual(self.parse_type("int?"), "int?")

    def test_custom_optional(self):
        self.assertEqual(self.parse_type("Widget?"), "Widget?")

    def test_regular_type_unchanged(self):
        self.assertEqual(self.parse_type("string"), "string")

    def test_optional_void_rejected(self):
        with self.assertRaises(ParserError):
            self.parse_type("void?")

    def test_double_question_rejected(self):
        with self.assertRaises(ParserError):
            self.parse_type("int??")

    def test_function_ast_type(self):
        program = Parser(Lexer("int? sample(int? value) { return value; }").tokenize()).parse()
        self.assertEqual(program[0].return_type, "int?")
        self.assertEqual(program[0].parameters[0].var_type, "int?")


if __name__ == "__main__":
    unittest.main()
