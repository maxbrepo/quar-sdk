"""Semantic binding tests for capture-free lambda expressions."""
import unittest
from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from frontend.quar.semantic import SemanticAnalyzer
from frontend.quar.errors import SemanticError


def analyze(source: str) -> SemanticAnalyzer:
    """Analyze source and return the analyzer containing callable bindings."""
    program = Parser(Lexer(source).tokenize()).parse()
    analyzer = SemanticAnalyzer()
    analyzer.analyze(program)
    return analyzer


class LambdaBindingTests(unittest.TestCase):
    def test_typed_lambda_binding(self):
        analyzer = analyze('function callback = lambda(int x)->int { return x + 1; };')
        signature = analyzer.bound_function_signature('callback')
        self.assertEqual(signature.parameter_types, ('int',))
        self.assertEqual(signature.return_type, 'int')

    def test_inferred_lambda_binding(self):
        analyzer = analyze('callback = lambda(int x)->int { return x; };')
        self.assertEqual(analyzer.bound_function_signature('callback').return_type, 'int')

    def test_lambda_signature_mismatch_rejected(self):
        with self.assertRaises(SemanticError):
            analyze('callback = lambda(int x)->int { return x; }; '
                    'callback = lambda(string x)->string { return x; };')

    def test_lambda_capture_rejected_in_binding(self):
        with self.assertRaises(SemanticError):
            analyze('int outside = 2; '
                    'function callback = lambda(int x)->int { return x + outside; };')


if __name__ == '__main__':
    unittest.main()
