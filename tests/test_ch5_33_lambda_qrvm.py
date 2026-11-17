"""End-to-end tests for capture-free lambda compilation."""
import unittest
from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from frontend.quar.semantic import SemanticAnalyzer
from qrvm.compiler import QRVMCompiler
from qrvm.vm import QRVM


class LambdaQRVMTests(unittest.TestCase):
    def run_source(self, source):
        program = Parser(Lexer(source).tokenize()).parse()
        SemanticAnalyzer().analyze(program)
        package = QRVMCompiler().compile(program)
        vm = QRVM()
        vm.functions = package['functions']
        variables = {}
        vm.execute(package['instructions'], variables)
        return variables, package

    def test_typed_lambda_executes(self):
        variables, package = self.run_source(
            'function callback = lambda(int x)->int { return x + 1; }; '
            'int result = (callback)(41);'
        )
        self.assertEqual(variables['result'], 42)
        self.assertIn('__quar_lambda_1', package['functions'])

    def test_two_lambdas_execute(self):
        variables, package = self.run_source(
            'function first = lambda(int x)->int { return x + 1; }; '
            'function second = lambda(int x)->int { return x + 2; }; '
            'int result = (first)(20) + (second)(20);'
        )
        self.assertEqual(variables['result'], 43)
        self.assertEqual(len([name for name in package['functions'] if name.startswith('__quar_lambda_')]), 2)


if __name__ == '__main__':
    unittest.main()
