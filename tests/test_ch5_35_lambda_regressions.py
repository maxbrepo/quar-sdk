"""Chapter 5.35: integration and stress checks for capture-free lambdas."""
import unittest

from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from frontend.quar.semantic import SemanticAnalyzer
from qrvm.compiler import QRVMCompiler
from qrvm.vm import QRVM


def execute(source: str):
    """Run a complete source and return globals and the compiled package."""
    program = Parser(Lexer(source).tokenize()).parse()
    SemanticAnalyzer().analyze(program)
    package = QRVMCompiler().compile(program)
    vm = QRVM()
    vm.functions = package['functions']
    variables = {}
    vm.execute(package['instructions'], variables)
    return variables, package


class LambdaRegressionTests(unittest.TestCase):
    def test_typed_function_variable(self):
        variables, _ = execute('function cb = lambda(int x)->int { return x + 1; }; int result = (cb)(41);')
        self.assertEqual(variables['result'], 42)

    def test_inferred_function_variable(self):
        variables, _ = execute('cb = lambda(int x)->int { return x + 1; }; int result = (cb)(41);')
        self.assertEqual(variables['result'], 42)

    def test_mixed_callback_forwarding(self):
        source = ('int apply(function(int)->int cb, int x) { return (cb)(x); } '
                  'int forward(function(int)->int cb, int x) { return apply(cb, x); } '
                  'cb = lambda(int x)->int { return x + 1; }; '
                  'int result = forward(cb, 41);')
        variables, _ = execute(source)
        self.assertEqual(variables['result'], 42)

    def test_many_generated_lambda_names(self):
        count = 40
        source = 'int __quar_lambda_1(int x) { return 999; } '
        source += ' '.join(f'function cb{i} = lambda(int x)->int {{ return x + {i}; }};' for i in range(count))
        source += f' int result = (cb{count - 1})(3); int original = __quar_lambda_1(0);'
        variables, package = execute(source)
        self.assertEqual(variables['result'], 42)
        self.assertEqual(variables['original'], 999)
        self.assertEqual(len(package['functions']), count + 1)

    def test_lambda_inside_named_function(self):
        variables, _ = execute('int compute(int x) { function cb = lambda(int y)->int { return y + 1; }; return (cb)(x); } int result = compute(41);')
        self.assertEqual(variables['result'], 42)


if __name__ == '__main__':
    unittest.main()
