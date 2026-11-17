"""Regression tests for callback signatures at ordinary call sites."""
import unittest
from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from frontend.quar.semantic import SemanticAnalyzer
from frontend.quar.errors import SemanticError


def analyze(source: str) -> None:
    """Analyze source and raise SemanticError for invalid callback arguments."""
    SemanticAnalyzer().analyze(Parser(Lexer(source).tokenize()).parse())


class CallbackSignatureValidationTests(unittest.TestCase):
    def test_compatible_callback(self):
        analyze('int identity(int x) { return x; }\n'
                'int apply(function(int)->int cb, int x) { return (cb)(x); }\n'
                'int result = apply(&identity, 42);')

    def test_incompatible_callback_return_type(self):
        with self.assertRaisesRegex(SemanticError, 'incompatible callback signature'):
            analyze('string convert(int x) { return "ok"; }\n'
                    'int apply(function(int)->int cb, int x) { return (cb)(x); }\n'
                    'int result = apply(&convert, 42);')

    def test_non_function_argument_rejected(self):
        with self.assertRaises(SemanticError):
            analyze('int apply(function(int)->int cb, int x) { return (cb)(x); }\n'
                    'int result = apply(7, 42);')


if __name__ == '__main__':
    unittest.main()
