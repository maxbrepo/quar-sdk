"""Verify native destructor configuration in the normal QRVM runner."""
import contextlib
import io
import subprocess
import tempfile
import unittest
from pathlib import Path

from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from frontend.quar.semantic import SemanticAnalyzer
from main import extract_native_release_options, run_qrvm
from qrvm.native_ffi import NativeFFIError


class NativeRunnerReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.library = Path(cls.temp.name) / "liblifetime.so"
        fixture = Path(__file__).resolve().parents[1] / "fixtures" / "qgf_ffi_lifetime.c"
        subprocess.run(["cc", "-shared", "-fPIC", str(fixture), "-o", str(cls.library)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def program(self, body):
        source = (
            'extern "C" opaque qgf_create_handle(); '
            'extern "C" i32 qgf_read_allocated(opaque handle); '
            'extern "C" void qgf_destroy_handle(opaque handle); '
            + body
        )
        program = Parser(Lexer(source).tokenize()).parse()
        SemanticAnalyzer().analyze(program)
        return program

    def test_extract_release_option(self):
        args, symbols = extract_native_release_options(["demo.vq", "--native-release", "qgf_destroy_handle"])
        self.assertEqual(args, ["demo.vq"])
        self.assertEqual(symbols, ("qgf_destroy_handle",))

    def test_duplicate_release_rejected(self):
        with self.assertRaises(ValueError):
            extract_native_release_options(["--native-release", "destroy", "--native-release", "destroy"])

    def test_invalid_release_option_rejected(self):
        with self.assertRaises(ValueError):
            extract_native_release_options(["--native-release", "--native-library"])

    def test_runner_create_read_destroy(self):
        program = self.program('handle = qgf_create_handle(); i32 value = qgf_read_allocated(handle); qgf_destroy_handle(handle);')
        with contextlib.redirect_stdout(io.StringIO()) as output:
            run_qrvm(program, native_library=str(self.library), native_release_symbols=("qgf_destroy_handle",))
        self.assertIn("Program executed successfully", output.getvalue())

    def test_runner_rejects_use_after_release(self):
        program = self.program('handle = qgf_create_handle(); qgf_destroy_handle(handle); i32 value = qgf_read_allocated(handle);')
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(NativeFFIError, "released"):
                run_qrvm(program, native_library=str(self.library), native_release_symbols=("qgf_destroy_handle",))

    def test_release_requires_library(self):
        with self.assertRaisesRegex(ValueError, "native-library"):
            run_qrvm(self.program('handle = qgf_create_handle();'), native_release_symbols=("qgf_destroy_handle",))

    def test_invalid_destructor_signature_rejected(self):
        with self.assertRaisesRegex(ValueError, "release symbol"):
            run_qrvm(self.program('handle = qgf_create_handle();'), native_library=str(self.library), native_release_symbols=("qgf_read_allocated",))


if __name__ == "__main__":
    unittest.main()
