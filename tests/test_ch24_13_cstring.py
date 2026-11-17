"""Test bounded UTF-8 C string arguments through the generic native bridge."""
import subprocess
import tempfile
import unittest
from pathlib import Path

from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from frontend.quar.semantic import SemanticAnalyzer
from qrvm.compiler import QRVMCompiler
from qrvm.native_ffi import NativeFFIError, NativeLibrary, NativeSignature
from qrvm.vm import QRVM


class CStringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.library = Path(cls.temp.name) / 'libcstring.so'
        fixture = Path(__file__).resolve().parents[1] / 'fixtures/qgf_ffi_cstring.c'
        subprocess.run(['cc', '-shared', '-fPIC', str(fixture), '-o', str(cls.library)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def execute(self, source):
        program = Parser(Lexer(source).tokenize()).parse()
        SemanticAnalyzer().analyze(program)
        package = QRVMCompiler().compile(program)
        vm = QRVM()
        vm.functions = package['functions']
        vm.bind_native(package['native_declarations'], NativeLibrary(self.library))
        variables = {}
        vm.execute(package['instructions'], variables)
        return variables

    def test_unicode_through_language(self):
        variables = self.execute('extern "C" i32 qgf_utf8_length(cstring text); '
                                 'i32 result = qgf_utf8_length("caffè");')
        self.assertEqual(variables['result'], 6)

    def test_utf8_content(self):
        variables = self.execute('extern "C" i32 qgf_utf8_match(cstring text); '
                                 'i32 result = qgf_utf8_match("caffè");')
        self.assertEqual(variables['result'], 1)

    def test_reject_embedded_nul(self):
        bridge = NativeLibrary(self.library)
        with self.assertRaisesRegex(NativeFFIError, 'embedded NUL'):
            bridge.call(NativeSignature('qgf_utf8_length', ('cstring',), 'i32'), 'a\x00b')

    def test_reject_non_text(self):
        bridge = NativeLibrary(self.library)
        with self.assertRaises(NativeFFIError):
            bridge.call(NativeSignature('qgf_utf8_length', ('cstring',), 'i32'), 42)

    def test_reject_cstring_return(self):
        with self.assertRaises(NativeFFIError):
            NativeSignature('qgf_utf8_length', (), 'cstring')


if __name__ == '__main__':
    unittest.main()
