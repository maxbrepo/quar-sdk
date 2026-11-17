"""Verify source-level native out declarations and safe FFI dispatch."""
import subprocess
import tempfile
import unittest
from pathlib import Path

from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from frontend.quar.semantic import SemanticAnalyzer
from frontend.quar.errors import ParserError, SemanticError
from qrvm.compiler import QRVMCompiler
from qrvm.vm import QRVM
from qrvm.native_ffi import NativeLibrary, NativeFFIError
from qrvm.native_composite_layout import NativeCompositeLayout

HEADER = '''extern "C" struct QGFOutPoint { i32 x; f64 y; u32 flags; };
extern "C" i32 qgf_fill_point(out QGFOutPoint point);
'''

def compile_source(source):
    ast = Parser(Lexer(source).tokenize()).parse()
    SemanticAnalyzer().analyze(ast)
    return QRVMCompiler().compile(ast)

class NativeOutDeclarationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        fixture = Path(__file__).resolve().parents[1] / 'fixtures/qgf_ffi_struct_out.c'
        cls.library_path = Path(cls.folder.name) / 'libout.so'
        subprocess.run(['cc', '-std=c11', '-shared', '-fPIC', str(fixture), '-o', str(cls.library_path)], check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def test_source_to_c_output(self):
        package = compile_source(HEADER + 'bytes result = qgf_fill_point();')
        self.assertEqual(package['native_output_declarations'], {'qgf_fill_point': 'QGFOutPoint'})
        self.assertNotIn('qgf_fill_point', package['native_declarations'])
        layout = NativeCompositeLayout('QGFOutPoint', 'struct', tuple(package['native_struct_layouts']['QGFOutPoint']))
        vm = QRVM()
        vm.bind_native(package['native_declarations'], NativeLibrary(self.library_path), output_layouts={'qgf_fill_point': layout})
        variables = {}
        vm.execute(package['instructions'], variables)
        result = layout.ctypes_type().from_buffer_copy(variables['result'])
        self.assertEqual((result.x, result.y, result.flags), (20, 2.5, 3))

    def test_reject_unknown_output_struct(self):
        with self.assertRaises(SemanticError):
            compile_source('extern "C" i32 qgf_fill_point(out Missing point);')

    def test_reject_incorrect_status_type(self):
        with self.assertRaises(SemanticError):
            compile_source('extern "C" struct Point { i32 x; }; extern "C" void qgf_fill_point(out Point p);')

    def test_reject_additional_parameters(self):
        with self.assertRaises(ParserError):
            compile_source('extern "C" i32 qgf_fill_point(out Point p, i32 n);')

    def test_native_error_propagates(self):
        package = compile_source(HEADER.replace('qgf_fill_point', 'qgf_fail_point') + 'bytes result = qgf_fail_point();')
        layout = NativeCompositeLayout('QGFOutPoint', 'struct', tuple(package['native_struct_layouts']['QGFOutPoint']))
        vm = QRVM()
        vm.bind_native({}, NativeLibrary(self.library_path), output_layouts={'qgf_fail_point': layout})
        with self.assertRaisesRegex(NativeFFIError, 'status 7'):
            vm.execute(package['instructions'], {})

if __name__ == '__main__':
    unittest.main()
