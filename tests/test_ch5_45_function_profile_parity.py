"""Chapter 5.45: parity checks for already supported function behavior.

No new language constructs are introduced by these tests.
"""
import unittest

from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from frontend.quar.semantic import SemanticAnalyzer
from qrvm.compiler import QRVMCompiler
from qrvm.vm import QRVM


def execute(source: str) -> dict:
    """Execute an existing Visual Quar program and return its globals."""
    program = Parser(Lexer(source).tokenize()).parse()
    SemanticAnalyzer().analyze(program)
    package = QRVMCompiler().compile(program)
    vm = QRVM()
    vm.functions = package['functions']
    variables = {}
    vm.execute(package['instructions'], variables)
    return variables


class FunctionProfileParityTests(unittest.TestCase):
    def test_typed_function_result(self):
        self.assertEqual(execute('int increment(int x) { return x + 1; } int result = increment(41);')['result'], 42)

    def test_inferred_function_result(self):
        self.assertEqual(execute('int increment(int x) { return x + 1; } result = increment(41);')['result'], 42)

    def test_mixed_function_result(self):
        self.assertEqual(execute('int increment(int x) { return x + 1; } value = 41; int result = increment(value);')['result'], 42)

    def test_typed_function_reference(self):
        self.assertEqual(execute('int increment(int x) { return x + 1; } function cb = &increment; int result = (cb)(41);')['result'], 42)

    def test_inferred_function_reference(self):
        self.assertEqual(execute('int increment(int x) { return x + 1; } cb = &increment; result = (cb)(41);')['result'], 42)

    def test_mixed_function_reference(self):
        self.assertEqual(execute('int increment(int x) { return x + 1; } cb = &increment; int result = (cb)(41);')['result'], 42)

    def test_typed_lambda(self):
        self.assertEqual(execute('function cb = lambda(int x)->int { return x + 1; }; int result = (cb)(41);')['result'], 42)

    def test_inferred_lambda(self):
        self.assertEqual(execute('cb = lambda(int x)->int { return x + 1; }; result = (cb)(41);')['result'], 42)

    def test_mixed_lambda(self):
        self.assertEqual(execute('cb = lambda(int x)->int { return x + 1; }; int result = (cb)(41);')['result'], 42)


if __name__ == '__main__':
    unittest.main()
