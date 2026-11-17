"""End-to-end native C struct values using named Visual Quar ABI declarations."""
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

DECLARATIONS = '''
extern "C" struct QGFPoint { i32 x; f64 y; u32 flags; };
extern "C" QGFPoint qgf_make_point_signed(i32 x, f64 y, i32 flags);
extern "C" f64 qgf_point_sum(QGFPoint point);
'''


def compile_source(source):
    ast = Parser(Lexer(source).tokenize()).parse()
    SemanticAnalyzer().analyze(ast)
    return QRVMCompiler().compile(ast)


class StructCallsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        fixture = Path(__file__).resolve().parents[1] / 'fixtures/qgf_ffi_struct_values.c'
        cls.library_path = Path(cls.folder.name) / 'libstruct_values.so'
        subprocess.run(['cc', '-std=c11', '-shared', '-fPIC', str(fixture), '-o', str(cls.library_path)], check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def test_nested_struct_roundtrip(self):
        package = compile_source(DECLARATIONS + 'f64 total = qgf_point_sum(qgf_make_point_signed(20, 2.5, 3));')
        vm = QRVM()
        vm.bind_native(package['native_declarations'], NativeLibrary(self.library_path), struct_layouts=package['native_struct_layouts'])
        variables = {}
        vm.execute(package['instructions'], variables)
        self.assertEqual(variables['total'], 25.5)

    def test_unknown_struct_rejected(self):
        with self.assertRaises(SemanticError):
            compile_source('extern "C" Unknown qgf_make_point();')

    def test_wrong_argument_rejected(self):
        with self.assertRaises(SemanticError):
            compile_source(DECLARATIONS + 'f64 total = qgf_point_sum(42);')

    def test_declarations_order_independent(self):
        source = 'extern "C" f64 qgf_point_sum(QGFPoint point); extern "C" struct QGFPoint { i32 x; f64 y; u32 flags; };'
        self.assertIn('native_struct_layouts', compile_source(source))


if __name__ == '__main__':
    unittest.main()
