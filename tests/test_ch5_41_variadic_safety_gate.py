"""Prevent unsupported variadic syntax from silently reaching QRVM."""
import unittest

from frontend.quar.errors import SemanticError
from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from frontend.quar.semantic import SemanticAnalyzer


def analyze(source: str) -> None:
    """Parse and validate source, raising on unsupported semantics."""
    program = Parser(Lexer(source).tokenize()).parse()
    SemanticAnalyzer().analyze(program)


class VariadicSafetyGateTests(unittest.TestCase):
    def test_variadic_declaration_rejected_explicitly(self):
        with self.assertRaisesRegex(SemanticError, 'variadic parameters'):
            analyze('int pick(int... values) { return 1; }')

    def test_variadic_with_fixed_prefix_rejected(self):
        with self.assertRaisesRegex(SemanticError, 'variadic parameters'):
            analyze('int pick(int x, int... values) { return x; }')

    def test_regular_function_still_works(self):
        analyze('int pick(int x) { return x; } int result = pick(42);')


if __name__ == '__main__':
    unittest.main()
