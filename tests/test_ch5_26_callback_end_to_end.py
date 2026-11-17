"""Chapter 5.26: callback integration and known signature-validation gap."""
import unittest
from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from frontend.quar.semantic import SemanticAnalyzer
from frontend.quar.errors import SemanticError
from qrvm.compiler import QRVMCompiler
from qrvm.vm import QRVM


class CallbackEndToEndTests(unittest.TestCase):
    def parse(self, source):
        return Parser(Lexer(source).tokenize()).parse()

    def test_callback_executes_from_source(self):
        source = (
            'int identity(int x) { return x; }\n'
            'int apply(function(int)->int cb, int x) { return (cb)(x); }\n'
            'int result = apply(&identity, 42);'
        )
        program = self.parse(source)
        SemanticAnalyzer().analyze(program)
        package = QRVMCompiler().compile(program)
        vm = QRVM()
        vm.functions = package['functions']
        variables = {}
        vm.execute(package['instructions'], variables)
        self.assertEqual(variables['result'], 42)

    def test_incompatible_callback_signature_is_rejected(self):
        """Reject callbacks whose argument types differ from the declared signature."""
        source = (
            'int identity(int x) { return x; }\n'
            'int apply(function(string)->int cb, int x) { return (cb)("ok"); }\n'
            'int result = apply(&identity, 42);'
        )
        with self.assertRaises(SemanticError):
            SemanticAnalyzer().analyze(self.parse(source))


if __name__ == '__main__':
    unittest.main()
