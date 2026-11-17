"""Chapter 43 cycle A: explicit native ownership and stale-handle rejection."""
from __future__ import annotations

import ctypes
from dataclasses import replace
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from frontend.quar.qir.program_lowering import lower_ast_program
from main import build_frontend
from qrvm.native_ffi import NativeFFIError, NativeLibrary, NativeSignature, OpaqueNativePointer
from qrvm.qir_program_backend import compile_qir_program
from qrvm.vm import QRVM


C_SOURCE = r'''
#include <stdint.h>
static int object = 42;
static int created = 0;
static int destroyed = 0;
void *native_create(void) { created++; return &object; }
int32_t native_read(void *ptr) { return ptr == &object ? object : -1; }
void native_destroy(void *ptr) { if (ptr == &object) destroyed++; }
int32_t native_created(void) { return created; }
int32_t native_destroyed(void) { return destroyed; }
'''


class NativeLifecycleCycleATests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = shutil.which('cc') or shutil.which('gcc')
        if not compiler:
            raise unittest.SkipTest('C compiler unavailable')
        cls.temp = tempfile.TemporaryDirectory()
        source = Path(cls.temp.name) / 'lifetime.c'
        cls.library_path = Path(cls.temp.name) / 'liblifetime.so'
        source.write_text(C_SOURCE, encoding='utf-8')
        subprocess.run([compiler, '-shared', '-fPIC', '-o', str(cls.library_path), str(source)],
                       check=True, capture_output=True, text=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.library = NativeLibrary(self.library_path)
        self.create = NativeSignature('native_create', (), 'opaque')
        self.read = NativeSignature('native_read', ('opaque',), 'i32')
        self.destroy = NativeSignature('native_destroy', ('opaque',), 'void')
        self.counter = ctypes.CDLL(str(self.library_path))
        self.counter.native_created.restype = ctypes.c_int32
        self.counter.native_destroyed.restype = ctypes.c_int32

    def test_create_read_release_and_reject_stale_read(self):
        handle = self.library.call(self.create)
        self.assertEqual(self.library.call(self.read, handle), 42)
        self.library.release_handle(handle, self.destroy)
        with self.assertRaisesRegex(NativeFFIError, 'released'):
            self.library.call(self.read, handle)

    def test_double_release_does_not_call_destructor_twice(self):
        handle = self.library.call(self.create)
        before = self.counter.native_destroyed()
        self.library.release_handle(handle, self.destroy)
        with self.assertRaisesRegex(NativeFFIError, 'released'):
            self.library.release_handle(handle, self.destroy)
        self.assertEqual(self.counter.native_destroyed(), before + 1)

    def test_forged_handle_token_rejected(self):
        handle = self.library.call(self.create)
        with self.assertRaisesRegex(NativeFFIError, 'registered'):
            self.library.call(self.read, replace(handle, token=0))
        self.library.release_handle(handle, self.destroy)

    def test_forged_address_rejected(self):
        handle = self.library.call(self.create)
        with self.assertRaisesRegex(NativeFFIError, 'registered'):
            self.library.release_handle(replace(handle, address=handle.address + 1), self.destroy)
        self.library.release_handle(handle, self.destroy)

    def test_cross_library_rejected(self):
        handle = self.library.call(self.create)
        other = NativeLibrary(self.library_path)
        with self.assertRaises(NativeFFIError):
            other.call(self.read, handle)
        self.library.release_handle(handle, self.destroy)

    def test_invalid_destructor_keeps_handle_live(self):
        handle = self.library.call(self.create)
        with self.assertRaisesRegex(NativeFFIError, 'destructor'):
            self.library.release_handle(handle, self.read)
        self.assertEqual(self.library.call(self.read, handle), 42)
        self.library.release_handle(handle, self.destroy)

    def test_qir_vm_explicit_release_and_order(self):
        source = ('extern "C" opaque native_create(); '
                  'extern "C" i32 native_read(opaque handle); '
                  'extern "C" void native_destroy(opaque handle); '
                  'opaque item = native_create(); '
                  'i32 value = native_read(item); native_destroy(item);')
        ast, _ = build_frontend(source)
        package = compile_qir_program(lower_ast_program(ast))
        vm = QRVM()
        vm.bind_native(package['native_declarations'], self.library, release_symbols=('native_destroy',))
        before = self.counter.native_destroyed()
        vm.run(package)
        self.assertEqual(self.counter.native_destroyed(), before + 1)
        self.assertEqual(vm.stack, [])

    def test_qir_vm_double_release_rejected(self):
        source = ('extern "C" opaque native_create(); '
                  'extern "C" void native_destroy(opaque handle); '
                  'opaque item = native_create(); native_destroy(item); native_destroy(item);')
        ast, _ = build_frontend(source)
        package = compile_qir_program(lower_ast_program(ast))
        vm = QRVM()
        vm.bind_native(package['native_declarations'], self.library, release_symbols=('native_destroy',))
        before = self.counter.native_destroyed()
        with self.assertRaisesRegex(NativeFFIError, 'released'):
            vm.run(package)
        self.assertEqual(self.counter.native_destroyed(), before + 1)

    def test_qir_vm_invalid_release_binding_rejected(self):
        vm = QRVM()
        with self.assertRaisesRegex(ValueError, 'release symbol'):
            vm.bind_native({'native_read': (('opaque',), 'i32')}, self.library,
                           release_symbols=('native_read',))


if __name__ == '__main__':
    unittest.main()
