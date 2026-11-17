"""Verify opaque C handles through the Visual Quar frontend and QRVM."""
import subprocess
import tempfile
import unittest
from pathlib import Path

from frontend.quar.errors import SemanticError
from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from frontend.quar.semantic import SemanticAnalyzer
from qrvm.compiler import QRVMCompiler
from qrvm.native_ffi import NativeFFIError, NativeLibrary, OpaqueNativePointer
from qrvm.vm import QRVM


class OpaqueLanguageBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.library_path = Path(cls.temporary.name) / "libopaque.so"
        fixture = Path(__file__).resolve().parents[1] / "fixtures" / "qgf_ffi_opaque.c"
        subprocess.run(["cc", "-shared", "-fPIC", str(fixture), "-o", str(cls.library_path)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def compile_source(self, source):
        program = Parser(Lexer(source).tokenize()).parse()
        SemanticAnalyzer().analyze(program)
        return QRVMCompiler().compile(program)

    def execute_source(self, source):
        package = self.compile_source(source)
        vm = QRVM()
        vm.functions = package["functions"]
        vm.bind_native(package["native_declarations"], NativeLibrary(self.library_path))
        variables = {}
        vm.execute(package["instructions"], variables)
        return variables

    def test_native_opaque_roundtrip(self):
        source = ('extern "C" opaque qgf_get_handle(); '
                  'extern "C" i32 qgf_read_handle(opaque handle); '
                  'handle = qgf_get_handle(); i32 result = qgf_read_handle(handle);')
        variables = self.execute_source(source)
        self.assertIsInstance(variables["handle"], OpaqueNativePointer)
        self.assertEqual(variables["result"], 42)

    def test_reject_integer_as_opaque_argument(self):
        source = 'extern "C" i32 qgf_read_handle(opaque handle); i32 result = qgf_read_handle(123);'
        with self.assertRaises((SemanticError, NativeFFIError)):
            self.execute_source(source)

    def test_reject_null_opaque_result(self):
        source = 'extern "C" opaque qgf_null_handle(); handle = qgf_null_handle();'
        with self.assertRaisesRegex(NativeFFIError, 'null opaque pointer'):
            self.execute_source(source)


if __name__ == "__main__":
    unittest.main()
