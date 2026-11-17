"""Chapter 5.23: function references through the complete QRVM source pipeline."""
import unittest

from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from frontend.quar.semantic import SemanticAnalyzer
from frontend.quar.errors import SemanticError
from qrvm.compiler import QRVMCompiler
from qrvm.vm import QRVM


class FunctionReferencePipelineTests(unittest.TestCase):
    def parse(self, source):
        return Parser(Lexer(source).tokenize()).parse()

    def run_source(self, source):
        program = self.parse(source)
        SemanticAnalyzer().analyze(program)
        package = QRVMCompiler().compile(program)
        vm = QRVM()
        vm.functions = package["functions"]
        variables = {}
        vm.execute(package["instructions"], variables)
        return variables

    def test_inferred_reference_from_source(self):
        result = self.run_source(
            "int identity(int x) { return x; }\n"
            "callback = &identity;\n"
            "result = (callback)(42);"
        )
        self.assertEqual(result["result"], 42)

    def test_typed_reference_from_source(self):
        result = self.run_source(
            "int identity(int x) { return x; }\n"
            "function callback = &identity;\n"
            "int result = (callback)(7);"
        )
        self.assertEqual(result["result"], 7)

    def test_wrong_argument_count_rejected(self):
        program = self.parse(
            "int identity(int x) { return x; }\n"
            "callback = &identity;\n"
            "result = (callback)();"
        )
        with self.assertRaises(SemanticError):
            SemanticAnalyzer().analyze(program)

    def test_non_function_typed_declaration_rejected(self):
        program = self.parse("function callback = 3;")
        with self.assertRaises(SemanticError):
            SemanticAnalyzer().analyze(program)


if __name__ == "__main__":
    unittest.main()
