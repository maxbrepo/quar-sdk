"""Chapter 43 cycle A: end-to-end ABI lifetime integration regressions."""
from __future__ import annotations

import ctypes.util
import os
import unittest
from unittest.mock import patch

from qrvm.native_ffi import NativeFFIError, NativeLibrary, NativeSignature
from qrvm.vm import QRVM

import test_ch43_cycle_a_sdl3_lifecycle as fixture

CREATE = fixture.CREATE
compile_source = fixture.compile_source


class FinalIntegrationTests(unittest.TestCase):
    """Reuse the compiled C fixture and assert full call sequencing."""

    setUpClass = classmethod(fixture.SDL3ManagedLifecycleTests.setUpClass.__func__)
    tearDownClass = classmethod(fixture.SDL3ManagedLifecycleTests.tearDownClass.__func__)
    setUp = fixture.SDL3ManagedLifecycleTests.setUp
    count = fixture.SDL3ManagedLifecycleTests.count
    run_managed = fixture.SDL3ManagedLifecycleTests.run_managed

    def test_full_success_sequence_with_explicit_quit(self):
        before = tuple(self.count(name) for name in ('init', 'create', 'destroy', 'quit'))
        try:
            self.run_managed(compile_source(CREATE))
        finally:
            self.library.call(NativeSignature('SDL_Quit', (), 'void'))
        after = tuple(self.count(name) for name in ('init', 'create', 'destroy', 'quit'))
        self.assertEqual(tuple(a - b for a, b in zip(after, before)), (1, 1, 1, 1))

    def test_full_failure_sequence_preserves_quit(self):
        before = tuple(self.count(name) for name in ('init', 'create', 'destroy', 'quit'))
        self.counters.set_fail_create(1)
        try:
            with self.assertRaisesRegex(NativeFFIError, 'null opaque'):
                self.run_managed(compile_source(CREATE))
        finally:
            self.library.call(NativeSignature('SDL_Quit', (), 'void'))
        after = tuple(self.count(name) for name in ('init', 'create', 'destroy', 'quit'))
        self.assertEqual(tuple(a - b for a, b in zip(after, before)), (1, 1, 0, 1))

    def test_repeated_vm_runs_release_each_window_once(self):
        before = self.count('destroy')
        for _ in range(3):
            self.run_managed()
        self.assertEqual(self.count('destroy') - before, 3)

    def test_explicit_destroy_then_exception_keeps_single_release(self):
        before = self.count('destroy')
        source = CREATE + 'SDL_DestroyWindow(window); SDL_DestroyWindow(window);'
        with self.assertRaisesRegex(NativeFFIError, 'released'):
            self.run_managed(compile_source(source))
        self.assertEqual(self.count('destroy') - before, 1)

    def test_real_sdl3_window_and_quit_if_available(self):
        name = ctypes.util.find_library('SDL3')
        if not name:
            self.skipTest('SDL3 shared library not found on this host')
        library = NativeLibrary(name)
        package = compile_source(CREATE)
        vm = QRVM()
        vm.bind_native(package['native_declarations'], library,
                       release_symbols=('SDL_DestroyWindow',))
        with patch.dict(os.environ, {'SDL_VIDEODRIVER': 'dummy'}):
            try:
                with library.managed_calls({
                    'SDL_CreateWindow': NativeSignature('SDL_DestroyWindow', ('opaque',), 'void')
                }):
                    vm.run(package)
            finally:
                library.call(NativeSignature('SDL_Quit', (), 'void'))


if __name__ == '__main__':
    unittest.main()
