"""End-to-end QIR native SDL3 contract using a compiled test double."""
from __future__ import annotations

import ctypes
import ctypes.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from frontend.quar.errors import SemanticError
from frontend.quar.qir.program_lowering import QIRProgramLoweringError, lower_ast_program
from main import build_frontend
from qrvm.native_ffi import NativeLibrary
from qrvm.qir_program_backend import compile_qir_program
from qrvm.vm import QRVM


SOURCE = (
    'extern "C" bool SDL_Init(u32 flags); '
    'extern "C" opaque SDL_CreateWindow(cstring title, i32 width, i32 height, u64 flags); '
    'extern "C" void SDL_DestroyWindow(opaque window); '
    'extern "C" void SDL_Quit(); '
    'u32 init_flags = 32; bool ready = SDL_Init(init_flags); '
    'u64 window_flags = 0; '
    'opaque window = SDL_CreateWindow("Quar SDL3", 320, 240, window_flags); '
    'SDL_DestroyWindow(window); SDL_Quit();'
)


class SDL3QIRPipelineTests(unittest.TestCase):
    def compile_source(self, source: str) -> dict:
        """Compile typed Visual Quar source to executable QIR/QRVM package."""
        ast, _ = build_frontend(source)
        return compile_qir_program(lower_ast_program(ast))

    def test_sdl3_abi_contract_compiles(self):
        package = self.compile_source(SOURCE)
        self.assertEqual(package['native_declarations']['SDL_CreateWindow'],
                         (('cstring', 'i32', 'i32', 'u64'), 'opaque'))

    def test_u64_maximum_literal(self):
        package = self.compile_source('extern "C" void take_flags(u64 flags); take_flags(18446744073709551615);')
        self.assertEqual(package['native_declarations']['take_flags'], (('u64',), 'void'))

    def test_u64_overflow_rejected(self):
        with self.assertRaises((SemanticError, QIRProgramLoweringError, ValueError)):
            self.compile_source('extern "C" void take_flags(u64 flags); take_flags(18446744073709551616);')

    def test_negative_u64_rejected(self):
        with self.assertRaises((SemanticError, QIRProgramLoweringError, ValueError)):
            self.compile_source('extern "C" void take_flags(u64 flags); take_flags(-1);')

    def test_compiled_native_stub_runs_full_lifecycle(self):
        compiler = shutil.which('cc') or shutil.which('gcc')
        if compiler is None:
            self.skipTest('C compiler not available')
        code = r'''
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
static int state = 0;
static int handle = 123;
bool SDL_Init(uint32_t flags) { if (flags != 32 || state != 0) return false; state = 1; return true; }
void *SDL_CreateWindow(const char *title, int32_t width, int32_t height, uint64_t flags) {
    if (state != 1 || strcmp(title, "Quar SDL3") || width != 320 || height != 240 || flags != 0) return 0;
    state = 2;
    return &handle;
}
void SDL_DestroyWindow(void *window) { if (state == 2 && window == &handle) state = 3; else state = -1; }
void SDL_Quit(void) { if (state == 3) state = 4; else state = -2; }
int get_state(void) { return state; }
'''
        with tempfile.TemporaryDirectory() as temp:
            c_file = Path(temp) / 'sdl3_stub.c'
            so_file = Path(temp) / 'libsdl3_stub.so'
            c_file.write_text(code, encoding='utf-8')
            subprocess.run([compiler, '-shared', '-fPIC', '-o', str(so_file), str(c_file)],
                           check=True, capture_output=True, text=True)
            package = self.compile_source(SOURCE)
            vm = QRVM()
            vm.bind_native(package['native_declarations'], NativeLibrary(so_file))
            vm.run(package)
            stub = ctypes.CDLL(str(so_file))
            stub.get_state.restype = ctypes.c_int
            self.assertEqual(stub.get_state(), 4)
            self.assertEqual(vm.stack, [])

    def test_real_sdl3_headless_optional(self):
        library = ctypes.util.find_library('SDL3')
        if not library:
            self.skipTest('SDL3 is not installed in this test environment')
        # The dummy video driver avoids creating a visible window in CI.
        import os
        from unittest.mock import patch
        with patch.dict(os.environ, {'SDL_VIDEODRIVER': 'dummy'}):
            package = self.compile_source(SOURCE)
            vm = QRVM()
            vm.bind_native(package['native_declarations'], NativeLibrary(library))
            vm.run(package)
            self.assertEqual(vm.stack, [])


if __name__ == '__main__':
    unittest.main()
