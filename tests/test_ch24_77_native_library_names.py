"""Regression coverage for native shared-library names and explicit paths."""
import ctypes.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from qrvm.native_ffi import NativeFFIError, NativeLibrary


class NativeLibraryNameTests(unittest.TestCase):
    def test_platform_library_name(self):
        name = ctypes.util.find_library('c')
        if not name:
            self.skipTest('C runtime library not found')
        library = NativeLibrary(name)
        self.assertIsNotNone(library)

    def test_explicit_missing_path(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(NativeFFIError, 'path not found'):
                NativeLibrary(Path(directory) / 'missing.so')

    def test_missing_soname(self):
        with self.assertRaisesRegex(NativeFFIError, 'Unable to load native library'):
            NativeLibrary('libvisualquar_ch24_missing_library_000.so')

    def test_invalid_names(self):
        for name in ('', '\x00', '..'):
            with self.subTest(name=repr(name)), self.assertRaises(NativeFFIError):
                NativeLibrary(name)

    def test_name_is_passed_to_dynamic_loader(self):
        with patch('qrvm.native_ffi.ctypes.CDLL') as loader:
            NativeLibrary('libSDL3.so.0')
            loader.assert_called_once_with('libSDL3.so.0')
