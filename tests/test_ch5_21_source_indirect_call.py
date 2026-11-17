"""Chapter 5.21: parse and execute an explicit indirect call from source."""
import unittest

from frontend.quar.ast_nodes import FunctionReference, IndirectFunctionCall
from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from qrvm.compiler import QRVMCompiler
from qrvm.instructions import OpCode
from qrvm.vm import QRVM


class SourceIndirectCallTests(unittest.TestCase):
    def parse(self, source):
        return Parser(Lexer(source).tokenize()).parse()

    def test_source_reference_call(self):
        statement = self.parse('result = (&identity)(42);')[0].value
        self.assertIsInstance(statement, IndirectFunctionCall)
        self.assertEqual(statement.callee, FunctionReference('identity'))
        vm = QRVM()
        vm.functions = {'identity': {'parameters': ['x'], 'return_type': 'int',
                       'instructions': [(OpCode.LOAD, 'x'), (OpCode.RETURN, True)]}}
        vm.execute(QRVMCompiler().compile_expression(statement), {})
        self.assertEqual(vm.stack.pop(), 42)

    def test_direct_call_is_unchanged(self):
        from frontend.quar.ast_nodes import FunctionCall
        self.assertIsInstance(self.parse('identity(42);')[0], FunctionCall)


if __name__ == '__main__':
    unittest.main()
