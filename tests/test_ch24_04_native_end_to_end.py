"""End-to-end scalar C ABI calls through the QRVM with explicit trusted binding."""
import subprocess
import tempfile
import unittest
from pathlib import Path

from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from frontend.quar.semantic import SemanticAnalyzer
from frontend.quar.errors import SemanticError
from qrvm.compiler import QRVMCompiler
from qrvm.vm import QRVM
from qrvm.native_ffi import NativeLibrary


class NativeEndToEndTests(unittest.TestCase):
    def compile_source(self, source):
        program = Parser(Lexer(source).tokenize()).parse()
        SemanticAnalyzer().analyze(program)
        return QRVMCompiler().compile(program)

    def test_call_c_from_visual_quar(self):
        fixture = Path(__file__).resolve().parents[1] / 'fixtures' / 'qgf_ffi_scalar.c'
        with tempfile.TemporaryDirectory() as temp:
            library_path = Path(temp) / 'libqgf_test.so'
            subprocess.run(['cc', '-shared', '-fPIC', str(fixture), '-o', str(library_path)], check=True)
            source = 'extern "C" i32 qgf_add(i32 a, i32 b); i32 result = qgf_add(20, 22);'
            package = self.compile_source(source)
            vm = QRVM()
            vm.functions = package['functions']
            vm.bind_native(package['native_declarations'], NativeLibrary(library_path))
            variables = {}
            vm.execute(package['instructions'], variables)
            self.assertEqual(variables['result'], 42)

    def test_reject_undeclared_native_call(self):
        with self.assertRaises(SemanticError):
            self.compile_source('i32 result = qgf_add(20, 22);')

    def test_reject_native_wrong_arity(self):
        with self.assertRaises(SemanticError):
            self.compile_source('extern "C" i32 qgf_add(i32 a, i32 b); i32 result = qgf_add(1);')

    def test_reject_duplicate_external(self):
        with self.assertRaises(SemanticError):
            self.compile_source('extern "C" i32 qgf_add(i32 a, i32 b); extern "C" i32 qgf_add(i32 a, i32 b);')

    def test_unbound_native_cannot_execute(self):
        package = self.compile_source('extern "C" i32 qgf_add(i32 a, i32 b); i32 result = qgf_add(1, 2);')
        vm = QRVM()
        vm.functions = package['functions']
        with self.assertRaisesRegex(RuntimeError, 'Unknown function'):
            vm.execute(package['instructions'], {})


if __name__ == '__main__':
    unittest.main()
