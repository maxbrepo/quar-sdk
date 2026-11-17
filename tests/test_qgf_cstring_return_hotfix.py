"""Regression tests for SDL3-style borrowed const char* return values."""
import ctypes.util
import unittest

from main import build_frontend
from frontend.quar.qir.program_lowering import lower_ast_program
from qrvm.qir_program_backend import compile_qir_program
from qrvm.native_ffi import NativeLibrary, NativeSignature, NativeFFIError
from qrvm.vm import QRVM


class CStringReturnHotfixTests(unittest.TestCase):
    def test_source_to_qir_return(self):
        source = 'extern "C" cstring getenv(cstring key); cstring name = getenv("PATH");'
        ast, _ = build_frontend(source)
        package = compile_qir_program(lower_ast_program(ast))
        self.assertEqual(package['native_declarations']['getenv'], (('cstring',), 'cstring'))

    def test_real_c_library_return(self):
        libc = ctypes.util.find_library('c')
        if not libc:
            self.skipTest('C runtime unavailable')
        library = NativeLibrary(libc)
        result = library.call(NativeSignature('getenv', ('cstring',), 'cstring'), 'PATH')
        self.assertIsInstance(result, str)
        self.assertTrue(result)

    def test_full_qir_vm(self):
        libc = ctypes.util.find_library('c')
        if not libc:
            self.skipTest('C runtime unavailable')
        ast, _ = build_frontend('extern "C" cstring getenv(cstring key); cstring value = getenv("PATH");')
        package = compile_qir_program(lower_ast_program(ast))
        vm = QRVM()
        vm.bind_native(package['native_declarations'], NativeLibrary(libc))
        vm.run(package)

    def test_null_return_rejected(self):
        libc = ctypes.util.find_library('c')
        if not libc:
            self.skipTest('C runtime unavailable')
        with self.assertRaisesRegex(NativeFFIError, 'null C string'):
            NativeLibrary(libc).call(NativeSignature('getenv', ('cstring',), 'cstring'), 'VQ_TEST_NONEXISTENT_7d52ab')

    def test_non_c_abi_rejected(self):
        with self.assertRaises(Exception):
            build_frontend('extern "Other" cstring getenv(cstring key);')


if __name__ == '__main__':
    unittest.main()
