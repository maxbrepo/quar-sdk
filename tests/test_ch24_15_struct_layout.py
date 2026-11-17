"""Compare explicit native structure layouts against compiled C ABI facts."""

import ctypes
from pathlib import Path
import subprocess
import tempfile
import unittest

from qrvm.native_struct_layout import NativeStructLayout, NativeStructLayoutError


class NativeStructLayoutTests(unittest.TestCase):
    def test_layout_matches_compiled_c(self):
        fixture = Path(__file__).resolve().parents[1] / "fixtures/qgf_ffi_struct_layout.c"
        with tempfile.TemporaryDirectory() as folder:
            library_path = Path(folder) / "libstruct_layout.so"
            subprocess.run(["cc", "-std=c11", "-shared", "-fPIC", str(fixture),
                            "-o", str(library_path)], check=True, capture_output=True)
            library = ctypes.CDLL(str(library_path))
            for symbol in ("size", "alignment", "x_offset", "y_offset", "flags_offset"):
                getattr(library, "qgf_point_" + symbol).restype = ctypes.c_size_t
            layout = NativeStructLayout("QGFPoint", (
                ("x", "i32"), ("y", "f64"), ("flags", "u32")))
            description = layout.describe()
            self.assertEqual(description["size"], library.qgf_point_size())
            self.assertEqual(description["alignment"], library.qgf_point_alignment())
            for name in ("x", "y", "flags"):
                self.assertEqual(description["offsets"][name],
                                 getattr(library, "qgf_point_" + name + "_offset")())

    def test_reject_duplicate_fields(self):
        with self.assertRaises(NativeStructLayoutError):
            NativeStructLayout("Point", (("x", "i32"), ("x", "i64")))

    def test_reject_unsupported_pointer_field(self):
        with self.assertRaises(NativeStructLayoutError):
            NativeStructLayout("Point", (("handle", "opaque"),))

    def test_reject_invalid_names(self):
        with self.assertRaises(NativeStructLayoutError):
            NativeStructLayout("Bad Name", (("x", "i32"),))

    def test_reject_empty_layout(self):
        with self.assertRaises(NativeStructLayoutError):
            NativeStructLayout("Empty", ())


if __name__ == "__main__":
    unittest.main()
