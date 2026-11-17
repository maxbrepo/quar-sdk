"""Chapter 43 cycle A: SDL3 resource lifetime through QIR and QRVM."""
from __future__ import annotations

import ctypes
import ctypes.util
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from frontend.quar.qir.program_lowering import lower_ast_program
from main import build_frontend
from qrvm.native_ffi import NativeFFIError, NativeLibrary, NativeSignature
from qrvm.qir_program_backend import compile_qir_program
from qrvm.vm import QRVM


DECLARATIONS = (
    'extern "C" bool SDL_Init(u32 flags); '
    'extern "C" opaque SDL_CreateWindow(cstring title, i32 width, i32 height, u64 flags); '
    'extern "C" void SDL_DestroyWindow(opaque window); '
    'extern "C" void SDL_Quit(); '
)
CREATE = 'u32 init_flags = 32; bool ready = SDL_Init(init_flags); u64 flags = 0; opaque window = SDL_CreateWindow("Quar", 320, 240, flags); '

STUB = r'''
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
static int handle = 42;
static int init_count = 0, create_count = 0, destroy_count = 0, quit_count = 0;
static int fail_create = 0;
bool SDL_Init(uint32_t flags) { init_count++; return flags == 32; }
void *SDL_CreateWindow(const char *title, int32_t w, int32_t h, uint64_t flags) {
    create_count++;
    if (fail_create || strcmp(title, "Quar") || w != 320 || h != 240 || flags != 0) return 0;
    return &handle;
}
void SDL_DestroyWindow(void *ptr) { if (ptr == &handle) destroy_count++; }
void SDL_Quit(void) { quit_count++; }
void set_fail_create(int value) { fail_create = value; }
int get_init_count(void) { return init_count; }
int get_create_count(void) { return create_count; }
int get_destroy_count(void) { return destroy_count; }
int get_quit_count(void) { return quit_count; }
'''


def compile_source(body: str) -> dict:
    """Return an executable package from the source-level native contract."""
    ast, _ = build_frontend(DECLARATIONS + body)
    return compile_qir_program(lower_ast_program(ast))


class SDL3ManagedLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = shutil.which('cc') or shutil.which('gcc')
        if compiler is None:
            raise unittest.SkipTest('C compiler unavailable')
        cls.temp = tempfile.TemporaryDirectory()
        source = Path(cls.temp.name) / 'sdl3_lifecycle.c'
        cls.path = Path(cls.temp.name) / 'libsdl3_lifecycle.so'
        source.write_text(STUB, encoding='utf-8')
        subprocess.run([compiler, '-shared', '-fPIC', '-o', str(cls.path), str(source)],
                       check=True, capture_output=True, text=True)
        cls.counters = ctypes.CDLL(str(cls.path))
        for name in ('get_init_count', 'get_create_count', 'get_destroy_count', 'get_quit_count'):
            getattr(cls.counters, name).restype = ctypes.c_int
        cls.counters.set_fail_create.argtypes = (ctypes.c_int,)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.counters.set_fail_create(0)
        self.library = NativeLibrary(self.path)
        self.destroy = NativeSignature('SDL_DestroyWindow', ('opaque',), 'void')
        self.package = compile_source(CREATE)

    def count(self, name: str) -> int:
        return getattr(self.counters, 'get_' + name + '_count')()

    def run_managed(self, package=None):
        vm = QRVM()
        vm.bind_native((package or self.package)['native_declarations'], self.library,
                       release_symbols=('SDL_DestroyWindow',))
        with self.library.managed_calls({'SDL_CreateWindow': self.destroy}):
            vm.run(package or self.package)
        return vm

    def test_success_releases_window_after_vm(self):
        before = self.count('destroy')
        self.run_managed()
        self.assertEqual(self.count('destroy'), before + 1)

    def test_explicit_destroy_is_not_repeated(self):
        before = self.count('destroy')
        self.run_managed(compile_source(CREATE + 'SDL_DestroyWindow(window);'))
        self.assertEqual(self.count('destroy'), before + 1)

    def test_double_destroy_is_rejected_without_second_native_call(self):
        before = self.count('destroy')
        with self.assertRaisesRegex(NativeFFIError, 'released'):
            self.run_managed(compile_source(CREATE + 'SDL_DestroyWindow(window); SDL_DestroyWindow(window);'))
        self.assertEqual(self.count('destroy'), before + 1)

    def test_vm_error_still_releases_window(self):
        before = self.count('destroy')
        with self.assertRaisesRegex(NativeFFIError, 'released'):
            self.run_managed(compile_source(CREATE + 'SDL_DestroyWindow(window); SDL_DestroyWindow(window);'))
        self.assertEqual(self.count('destroy'), before + 1)

    def test_null_window_does_not_trigger_destructor(self):
        self.counters.set_fail_create(1)
        before = self.count('destroy')
        with self.assertRaisesRegex(NativeFFIError, 'null opaque'):
            self.run_managed()
        self.assertEqual(self.count('destroy'), before)

    def test_quit_is_guaranteed_by_host_finally_on_vm_error(self):
        before = self.count('quit')
        package = compile_source(CREATE + 'SDL_DestroyWindow(window); SDL_DestroyWindow(window);')
        try:
            with self.assertRaisesRegex(NativeFFIError, 'released'):
                self.run_managed(package)
        finally:
            self.library.call(NativeSignature('SDL_Quit', (), 'void'))
        self.assertEqual(self.count('quit'), before + 1)

    def test_initialization_failure_does_not_create_a_window(self):
        package = compile_source('u32 flags = 0; bool ready = SDL_Init(flags);')
        before = self.count('create')
        self.run_managed(package)
        self.assertEqual(self.count('create'), before)

    def test_real_sdl3_optional(self):
        name = ctypes.util.find_library('SDL3')
        if not name:
            self.skipTest('SDL3 unavailable; run on host with SDL3')
        library = NativeLibrary(name)
        vm = QRVM()
        vm.bind_native(self.package['native_declarations'], library,
                       release_symbols=('SDL_DestroyWindow',))
        with patch.dict(os.environ, {'SDL_VIDEODRIVER': 'dummy'}):
            try:
                with library.managed_calls({'SDL_CreateWindow': self.destroy}):
                    vm.run(self.package)
            finally:
                library.call(NativeSignature('SDL_Quit', (), 'void'))
