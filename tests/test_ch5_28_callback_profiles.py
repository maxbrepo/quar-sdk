"""Chapter 5.28: callback execution across declaration styles and forwarding."""
import unittest
from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from frontend.quar.semantic import SemanticAnalyzer
from frontend.quar.errors import SemanticError
from qrvm.compiler import QRVMCompiler
from qrvm.vm import QRVM


def execute(source: str) -> dict:
    """Compile and run a complete source; return the global variables."""
    program = Parser(Lexer(source).tokenize()).parse()
    SemanticAnalyzer().analyze(program)
    package = QRVMCompiler().compile(program)
    vm = QRVM()
    vm.functions = package['functions']
    result = {}
    vm.execute(package['instructions'], result)
    return result


class CallbackProfilesTests(unittest.TestCase):
    def test_typed_callback(self):
        variables = execute('int identity(int x) { return x; }\n'
                            'int apply(function(int)->int cb, int x) { return (cb)(x); }\n'
                            'int result = apply(&identity, 42);')
        self.assertEqual(variables['result'], 42)

    def test_inferred_result(self):
        variables = execute('int identity(int x) { return x; }\n'
                            'int apply(function(int)->int cb, int x) { return (cb)(x); }\n'
                            'result = apply(&identity, 17);')
        self.assertEqual(variables['result'], 17)

    def test_mixed_reference_variable(self):
        variables = execute('int identity(int x) { return x; }\n'
                            'int apply(function(int)->int cb, int x) { return (cb)(x); }\n'
                            'callback = &identity;\n'
                            'int result = apply(callback, 23);')
        self.assertEqual(variables['result'], 23)

    def test_mismatched_signature_through_variable_rejected(self):
        source = ('string convert(int x) { return "ok"; }\n'
                  'int apply(function(int)->int cb, int x) { return (cb)(x); }\n'
                  'callback = &convert;\n'
                  'int result = apply(callback, 2);')
        with self.assertRaises(SemanticError):
            execute(source)

    def test_callback_forwarded_through_two_functions(self):
        variables = execute('int identity(int x) { return x; }\n'
                            'int apply(function(int)->int cb, int x) { return (cb)(x); }\n'
                            'int forward(function(int)->int cb, int x) { return apply(cb, x); }\n'
                            'int result = forward(&identity, 31);')
        self.assertEqual(variables['result'], 31)


if __name__ == '__main__':
    unittest.main()
