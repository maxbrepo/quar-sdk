"""Experimental source syntax for callback parameter signatures."""
import unittest
from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from frontend.quar.semantic import SemanticAnalyzer
from frontend.quar.function_types import FunctionSignature
from frontend.quar.errors import SemanticError


class CallbackSignatureParserTests(unittest.TestCase):
    def parse(self, source):
        return Parser(Lexer(source).tokenize()).parse()

    def test_signature_is_preserved_in_ast(self):
        program = self.parse('int apply(function(int)->int cb, int x) { return (cb)(x); }')
        function = program.statements[0] if hasattr(program, 'statements') else program[0]
        self.assertEqual(function.parameters[0].callback_signature, FunctionSignature(('int',), 'int'))

    def test_callback_body_is_checked(self):
        SemanticAnalyzer().analyze(self.parse('int apply(function(int)->int cb, int x) { return (cb)(x); }'))

    def test_bad_callback_arity_is_rejected(self):
        program = self.parse('int apply(function(int)->int cb) { return (cb)(1, 2); }')
        with self.assertRaisesRegex(SemanticError, 'expects 1 arguments'):
            SemanticAnalyzer().analyze(program)

    def test_regular_function_parameter_unchanged(self):
        program = self.parse('int identity(int x) { return x; }')
        function = program.statements[0] if hasattr(program, 'statements') else program[0]
        self.assertIsNone(function.parameters[0].callback_signature)


if __name__ == '__main__':
    unittest.main()
