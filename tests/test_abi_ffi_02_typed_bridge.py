"""Test the explicit scalar native bridge against a compiled C fixture."""

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from qrvm.native_ffi import NativeFFIError, NativeLibrary, NativeSignature


@unittest.skipUnless(shutil.which("cc"), "A C compiler is required")
class NativeTypedBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.library_path = Path(cls.temp.name) / "libqgf_ffi_scalar.so"
        subprocess.run([
            "cc", "-std=c99", "-Wall", "-Wextra", "-Werror", "-fPIC", "-shared",
            str(ROOT / "fixtures" / "qgf_ffi_scalar.c"), "-o", str(cls.library_path),
        ], check=True, capture_output=True, timeout=15)
        cls.bridge = NativeLibrary(cls.library_path)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_add(self):
        signature = NativeSignature("qgf_add", ("i32", "i32"), "i32")
        self.assertEqual(self.bridge.call(signature, 20, 22), 42)
        self.assertEqual(self.bridge.call(signature, -4, 2), -2)

    def test_subtract(self):
        self.assertEqual(self.bridge.call(NativeSignature("qgf_subtract", ("i32", "i32"), "i32"), 9, 4), 5)

    def test_wrong_arity(self):
        with self.assertRaises(NativeFFIError):
            self.bridge.call(NativeSignature("qgf_add", ("i32", "i32"), "i32"), 1)

    def test_integer_overflow_and_bool(self):
        signature = NativeSignature("qgf_add", ("i32", "i32"), "i32")
        for invalid in (2 ** 31, -(2 ** 31) - 1, True, 2.0):
            with self.subTest(value=invalid), self.assertRaises(NativeFFIError):
                self.bridge.call(signature, invalid, 0)

    def test_invalid_signature(self):
        with self.assertRaises(NativeFFIError):
            NativeSignature("qgf_add", ("pointer",), "i32")

    def test_missing_symbol(self):
        with self.assertRaises(NativeFFIError):
            self.bridge.call(NativeSignature("qgf_missing", (), "i32"))

    def test_conflicting_symbol_signature(self):
        self.bridge.call(NativeSignature("qgf_add", ("i32", "i32"), "i32"), 1, 2)
        with self.assertRaises(NativeFFIError):
            self.bridge.call(NativeSignature("qgf_add", ("u32", "u32"), "u32"), 1, 2)

    def test_missing_library(self):
        with self.assertRaises(FileNotFoundError):
            NativeLibrary(Path(self.temp.name) / "missing.so")


if __name__ == "__main__":
    unittest.main()
