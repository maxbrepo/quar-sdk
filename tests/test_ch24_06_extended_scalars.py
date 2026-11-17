"""Verify explicit scalar C ABI signatures and Visual Quar declarations."""
import subprocess
import tempfile
import unittest
from pathlib import Path

from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from frontend.quar.semantic import SemanticAnalyzer
from qrvm.compiler import QRVMCompiler
from qrvm.vm import QRVM
from qrvm.native_ffi import NativeFFIError, NativeLibrary, NativeSignature


class ExtendedScalarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        fixture = Path(__file__).resolve().parents[1] / 'fixtures' / 'qgf_ffi_extended.c'
        cls.library_path = Path(cls.temp.name) / 'libqgf_extended.so'
        subprocess.run(['cc', '-shared', '-fPIC', str(fixture), '-o', str(cls.library_path)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_integer_64(self):
        bridge = NativeLibrary(self.library_path)
        self.assertEqual(bridge.call(NativeSignature('qgf_add64', ('i64', 'i64'), 'i64'), 20, 22), 42)
        self.assertEqual(bridge.call(NativeSignature('qgf_add_unsigned64', ('u64', 'u64'), 'u64'), 20, 22), 42)

    def test_float_scalars(self):
        bridge = NativeLibrary(self.library_path)
        self.assertAlmostEqual(bridge.call(NativeSignature('qgf_multiply_f32', ('f32', 'f32'), 'f32'), 1.5, 2.0), 3.0)
        self.assertAlmostEqual(bridge.call(NativeSignature('qgf_multiply_f64', ('f64', 'f64'), 'f64'), 1.5, 2.0), 3.0)

    def test_void_result(self):
        bridge = NativeLibrary(self.library_path)
        self.assertIsNone(bridge.call(NativeSignature('qgf_set_value', ('i32',), 'void'), 42))
        self.assertEqual(bridge.call(NativeSignature('qgf_get_value', (), 'i32')), 42)

    def test_reject_invalid_scalar(self):
        bridge = NativeLibrary(self.library_path)
        with self.assertRaises(NativeFFIError):
            bridge.call(NativeSignature('qgf_add64', ('i64', 'i64'), 'i64'), 2 ** 63, 1)
        with self.assertRaises(NativeFFIError):
            bridge.call(NativeSignature('qgf_multiply_f64', ('f64', 'f64'), 'f64'), True, 1.0)

    def test_visual_quar_i64_call(self):
        source = 'extern "C" i64 qgf_add64(i64 a, i64 b); i64 result = qgf_add64(20, 22);'
        program = Parser(Lexer(source).tokenize()).parse()
        SemanticAnalyzer().analyze(program)
        package = QRVMCompiler().compile(program)
        vm = QRVM()
        vm.functions = package['functions']
        vm.bind_native(package['native_declarations'], NativeLibrary(self.library_path))
        variables = {}
        vm.execute(package['instructions'], variables)
        self.assertEqual(variables['result'], 42)


if __name__ == '__main__':
    unittest.main()
