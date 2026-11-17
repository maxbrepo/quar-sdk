"""Semantic checks for capture-free lambdas; execution is not supported yet."""
import unittest
from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from frontend.quar.semantic import SemanticAnalyzer
from frontend.quar.errors import SemanticError


def check(source: str) -> None:
    """Analyze a full program and raise if semantic validation fails."""
    parser = Parser(Lexer(source).tokenize())
    expression = parser.parse_expression()
    analyzer = SemanticAnalyzer()
    analyzer.variables["outside"] = "int"
    analyzer.analyze_expression(expression)


class LambdaSemanticTests(unittest.TestCase):
    def test_valid_lambda_expression(self):
        check('lambda(int x)->int { return x + 1; };')

    def test_void_lambda(self):
        check('lambda()->void { };')

    def test_return_type_mismatch(self):
        with self.assertRaises(SemanticError):
            check('lambda(int x)->string { return x; };')

    def test_missing_return(self):
        with self.assertRaises(SemanticError):
            check('lambda(int x)->int { int y = x; };')

    def test_implicit_capture_rejected(self):
        with self.assertRaises(SemanticError):
            check('lambda(int x)->int { return x + outside; }')

    def test_duplicate_parameters_rejected(self):
        with self.assertRaises(SemanticError):
            check('lambda(int x, int x)->int { return x; };')


if __name__ == '__main__':
    unittest.main()
