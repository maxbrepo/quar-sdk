"""Verify a minimal native C ABI fixture before wiring Visual Quar source calls."""

import ctypes
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "fixtures" / "qgf_ffi_scalar.c"


@unittest.skipUnless(shutil.which("cc"), "A C compiler is required")
class NativeScalarAbiProbe(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.library_path = Path(self.directory.name) / "libqgf_ffi_scalar.so"
        subprocess.run(
            ["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", "-fPIC",
             "-shared", str(SOURCE), "-o", str(self.library_path)],
            check=True, capture_output=True, text=True, timeout=15,
        )
        self.library = ctypes.CDLL(str(self.library_path))

    def test_add_i32(self):
        function = self.library.qgf_add
        function.argtypes = (ctypes.c_int32, ctypes.c_int32)
        function.restype = ctypes.c_int32
        for left, right, expected in ((2, 3, 5), (-10, 4, -6), (0, 0, 0)):
            with self.subTest(left=left, right=right):
                self.assertEqual(function(left, right), expected)

    def test_subtract_i32(self):
        function = self.library.qgf_subtract
        function.argtypes = (ctypes.c_int32, ctypes.c_int32)
        function.restype = ctypes.c_int32
        self.assertEqual(function(8, 3), 5)

    def test_missing_symbol_is_rejected(self):
        with self.assertRaises(AttributeError):
            getattr(self.library, "qgf_missing_symbol")

    def test_missing_library_is_rejected(self):
        with self.assertRaises(OSError):
            ctypes.CDLL(str(Path(self.directory.name) / "missing.so"))


if __name__ == "__main__":
    unittest.main()
