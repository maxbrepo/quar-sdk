"""Chapter 5.34: lambda interoperability and generated-name regression tests."""
import unittest

from frontend.quar.errors import SemanticError
from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from frontend.quar.semantic import SemanticAnalyzer
from qrvm.compiler import QRVMCompiler
from qrvm.vm import QRVM


def run_source(source: str) -> dict:
    """Analyze, compile and execute a source, returning its global variables."""
    program = Parser(Lexer(source).tokenize()).parse()
    SemanticAnalyzer().analyze(program)
    package = QRVMCompiler().compile(program)
    vm = QRVM()
    vm.functions = package['functions']
    variables = {}
    vm.execute(package['instructions'], variables)
    return variables


class LambdaIntegrationTests(unittest.TestCase):
    def test_lambda_variable_as_callback(self):
        result = run_source('int apply(function(int)->int cb, int x) { return (cb)(x); } '
                            'function cb = lambda(int x)->int { return x + 3; }; '
                            'int result = apply(cb, 39);')
        self.assertEqual(result['result'], 42)

    def test_direct_lambda_as_callback(self):
        result = run_source('int apply(function(int)->int cb, int x) { return (cb)(x); } '
                            'int result = apply(lambda(int x)->int { return x + 3; }, 39);')
        self.assertEqual(result['result'], 42)

    def test_direct_lambda_signature_mismatch_rejected(self):
        with self.assertRaises(SemanticError):
            run_source('int apply(function(int)->int cb, int x) { return (cb)(x); } '
                       'int result = apply(lambda(string x)->int { return 3; }, 39);')

    def test_inferred_lambda_variable(self):
        result = run_source('cb = lambda(int x)->int { return x + 3; }; '
                            'int result = (cb)(39);')
        self.assertEqual(result['result'], 42)

    def test_nested_indirect_lambda_calls(self):
        result = run_source('function a = lambda(int x)->int { return x + 1; }; '
                            'function b = lambda(int x)->int { return x + 2; }; '
                            'int result = (a)((b)(39));')
        self.assertEqual(result['result'], 42)

    def test_generated_lambda_name_avoids_user_function(self):
        result = run_source('int __quar_lambda_1(int x) { return 99; } '
                            'function a = lambda(int x)->int { return x + 1; }; '
                            'int result = (a)(41); int other = __quar_lambda_1(1);')
        self.assertEqual(result['result'], 42)
        self.assertEqual(result['other'], 99)


if __name__ == '__main__':
    unittest.main()
