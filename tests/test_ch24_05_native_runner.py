"""Test explicit native library selection in the normal QRVM entry point."""
import contextlib
import io
import subprocess
import tempfile
import unittest
from pathlib import Path

from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from frontend.quar.semantic import SemanticAnalyzer
from main import extract_native_library_option, run_qrvm


class NativeRunnerTests(unittest.TestCase):
    def test_extract_library_option(self):
        args, path = extract_native_library_option(['demo.vq', '--native-library', '/tmp/libdemo.so'])
        self.assertEqual(args, ['demo.vq'])
        self.assertEqual(path, '/tmp/libdemo.so')

    def test_missing_library_argument(self):
        with self.assertRaises(ValueError):
            extract_native_library_option(['demo.vq', '--native-library'])

    def test_duplicate_library_argument(self):
        with self.assertRaises(ValueError):
            extract_native_library_option(['--native-library', 'one', '--native-library', 'two'])

    def test_runner_calls_native_library(self):
        fixture = Path(__file__).resolve().parents[1] / 'fixtures' / 'qgf_ffi_scalar.c'
        with tempfile.TemporaryDirectory() as temp:
            library = Path(temp) / 'libqgf.so'
            subprocess.run(['cc', '-shared', '-fPIC', str(fixture), '-o', str(library)], check=True)
            source = 'extern "C" i32 qgf_add(i32 a, i32 b); i32 result = qgf_add(20, 22);'
            program = Parser(Lexer(source).tokenize()).parse()
            SemanticAnalyzer().analyze(program)
            with contextlib.redirect_stdout(io.StringIO()) as output:
                run_qrvm(program, native_library=str(library))
            self.assertIn('Program executed successfully', output.getvalue())

    def test_runner_rejects_missing_binding(self):
        source = 'extern "C" i32 qgf_add(i32 a, i32 b); i32 result = qgf_add(20, 22);'
        program = Parser(Lexer(source).tokenize()).parse()
        SemanticAnalyzer().analyze(program)
        with self.assertRaisesRegex(RuntimeError, 'native-library'):
            run_qrvm(program)


if __name__ == '__main__':
    unittest.main()
