"""Required real-SDL3 smoke tests for Chapter 43 cycle A release validation.

Run explicitly; this file is deliberately outside the test_ch43_*.py pattern.
"""
from __future__ import annotations

import ctypes.util
import os
import unittest
from unittest.mock import patch

from qrvm.native_ffi import NativeLibrary, NativeSignature
from qrvm.vm import QRVM
from test_ch43_cycle_a_sdl3_lifecycle import CREATE, compile_source


class RequiredSDL3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        name = ctypes.util.find_library('SDL3')
        if not name:
            raise AssertionError(
                'SDL3 real-library validation REQUIRED but SDL3 was not found. '
                'Install SDL3 or configure the system dynamic linker, then rerun.'
            )
        cls.library_name = name

    def run_real_window(self) -> None:
        """Execute the source/QIR/QRVM/ABI path and always call SDL_Quit."""
        library = NativeLibrary(self.library_name)
        package = compile_source(CREATE)
        vm = QRVM()
        vm.bind_native(package['native_declarations'], library,
                       release_symbols=('SDL_DestroyWindow',))
        destroy = NativeSignature('SDL_DestroyWindow', ('opaque',), 'void')
        with patch.dict(os.environ, {'SDL_VIDEODRIVER': 'dummy'}):
            try:
                with library.managed_calls({'SDL_CreateWindow': destroy}):
                    vm.run(package)
            finally:
                library.call(NativeSignature('SDL_Quit', (), 'void'))

    def test_real_sdl3_window_lifecycle(self):
        self.run_real_window()

    def test_real_sdl3_reinitialization_after_cleanup(self):
        self.run_real_window()
        self.run_real_window()


if __name__ == '__main__':
    unittest.main()
