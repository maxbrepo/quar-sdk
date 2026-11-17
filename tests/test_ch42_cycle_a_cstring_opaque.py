"""Native C string and opaque handle transport across source, QIR and QRVM."""
import ctypes.util
import unittest
from main import build_frontend
from frontend.quar.qir.program_lowering import lower_ast_program, QIRProgramLoweringError
from qrvm.qir_program_backend import compile_qir_program
from qrvm.native_ffi import NativeLibrary
from qrvm.vm import QRVM
from frontend.quar.errors import SemanticError


class NativeStringOpaqueTests(unittest.TestCase):
    def package(self, source):
        ast, _ = build_frontend(source)
        return compile_qir_program(lower_ast_program(ast))

    def test_cstring_source_and_qir(self):
        package = self.package('extern "C" i32 puts(cstring text); i32 result = puts("Quar QIR UTF-8"); print(result);')
        self.assertEqual(package['native_declarations']['puts'], (('cstring',), 'i32'))
        self.assertTrue(any(op[0].name == 'PUSH_STRING' for op in package['instructions']))

    def test_real_libc_string(self):
        libc = ctypes.util.find_library('c')
        if not libc:
            self.skipTest('C library unavailable')
        package = self.package('extern "C" i32 puts(cstring text); i32 result = puts("Quar native string");')
        vm = QRVM()
        vm.bind_native(package['native_declarations'], NativeLibrary(libc))
        vm.run(package)
        self.assertEqual(vm.stack, [])

    def test_opaque_window_source_pipeline(self):
        source = ('extern "C" opaque SDL_CreateWindow(cstring title, i32 width, i32 height, u32 flags); '
                  'extern "C" void SDL_DestroyWindow(opaque window); '
                  'opaque window = SDL_CreateWindow("Quar", 320, 240, 0); SDL_DestroyWindow(window);')
        package = self.package(source)
        self.assertEqual(package['native_declarations']['SDL_CreateWindow'],
                         (('cstring', 'i32', 'i32', 'u32'), 'opaque'))
        self.assertEqual(package['native_declarations']['SDL_DestroyWindow'], (('opaque',), 'void'))

    def test_negative_u32_literal_rejected(self):
        with self.assertRaises((ValueError, QIRProgramLoweringError, SemanticError)):
            self.package('extern "C" void native_set(u32 flags); native_set(-1);')

    def test_oversize_u32_literal_rejected(self):
        with self.assertRaises((ValueError, QIRProgramLoweringError, SemanticError)):
            self.package('extern "C" void native_set(u32 flags); native_set(4294967296);')

    def test_embedded_nul_rejected_at_lowering(self):
        from frontend.quar.ast_nodes import ExternalFunctionDeclaration, FunctionParameter, FunctionCall, String
        with self.assertRaisesRegex(QIRProgramLoweringError, 'NUL'):
            lower_ast_program([ExternalFunctionDeclaration('C', 'void', 'native_set',
                               [FunctionParameter('cstring', 'text')]),
                               FunctionCall('native_set', [String('bad\x00text')])])


if __name__ == '__main__':
    unittest.main()
