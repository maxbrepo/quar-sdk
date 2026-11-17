"""Validate explicit C resource release through a Visual Quar program."""
import subprocess
import tempfile
import unittest
from pathlib import Path

from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from frontend.quar.semantic import SemanticAnalyzer
from qrvm.compiler import QRVMCompiler
from qrvm.native_ffi import NativeFFIError, NativeLibrary
from qrvm.vm import QRVM


class NativeLanguageReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.path = Path(cls.temp.name) / "liblifetime.so"
        fixture = Path(__file__).resolve().parents[1] / "fixtures" / "qgf_ffi_lifetime.c"
        subprocess.run(["cc", "-shared", "-fPIC", str(fixture), "-o", str(cls.path)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def execute(self, body, *, release_symbols=("qgf_destroy_handle",)):
        source = (
            'extern "C" opaque qgf_create_handle(); '
            'extern "C" i32 qgf_read_allocated(opaque handle); '
            'extern "C" void qgf_destroy_handle(opaque handle); '
            + body
        )
        program = Parser(Lexer(source).tokenize()).parse()
        SemanticAnalyzer().analyze(program)
        package = QRVMCompiler().compile(program)
        vm = QRVM()
        vm.functions = package["functions"]
        vm.bind_native(package["native_declarations"], NativeLibrary(self.path), release_symbols=release_symbols)
        variables = {}
        vm.execute(package["instructions"], variables)
        return variables

    def test_create_read_release(self):
        result = self.execute('handle = qgf_create_handle(); i32 result = qgf_read_allocated(handle); qgf_destroy_handle(handle);')
        self.assertEqual(result["result"], 42)

    def test_use_after_release_rejected(self):
        with self.assertRaisesRegex(NativeFFIError, "released"):
            self.execute('handle = qgf_create_handle(); qgf_destroy_handle(handle); i32 result = qgf_read_allocated(handle);')

    def test_double_release_rejected(self):
        with self.assertRaisesRegex(NativeFFIError, "released"):
            self.execute('handle = qgf_create_handle(); qgf_destroy_handle(handle); qgf_destroy_handle(handle);')

    def test_invalid_release_signature_rejected(self):
        with self.assertRaisesRegex(ValueError, "release symbol"):
            self.execute('handle = qgf_create_handle();', release_symbols=("qgf_read_allocated",))


if __name__ == "__main__":
    unittest.main()
