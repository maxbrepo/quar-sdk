"""Verify general C struct-by-value calls through the native FFI bridge."""
import subprocess
import tempfile
import unittest
from pathlib import Path

from qrvm.native_ffi import NativeFFIError, NativeLibrary, NativeSignature, NativeStructValue
from qrvm.native_struct_layout import NativeStructLayout


class NativeStructValueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        fixture = Path(__file__).resolve().parents[1] / "fixtures/qgf_ffi_struct_values.c"
        cls.path = Path(cls.folder.name) / "libstruct_values.so"
        subprocess.run(["cc", "-std=c11", "-shared", "-fPIC", str(fixture), "-o", str(cls.path)],
                       check=True, capture_output=True)
        cls.layout = NativeStructLayout("QGFPoint", (("x", "i32"), ("y", "f64"), ("flags", "u32")))

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def test_struct_return_and_argument_by_value(self):
        library = NativeLibrary(self.path)
        point = library.call(NativeSignature("qgf_make_point", ("i32", "f64", "u32"), self.layout), 20, 2.5, 3)
        self.assertEqual(point, NativeStructValue(self.layout, (20, 2.5, 3)))
        self.assertEqual(library.call(NativeSignature("qgf_point_sum", (self.layout,), "f64"), point), 25.5)

    def test_reject_wrong_layout(self):
        library = NativeLibrary(self.path)
        wrong = NativeStructLayout("Other", (("x", "i32"),))
        with self.assertRaises(NativeFFIError):
            library.call(NativeSignature("qgf_point_sum", (self.layout,), "f64"), NativeStructValue(wrong, (3,)))

    def test_reject_out_of_range_field(self):
        library = NativeLibrary(self.path)
        with self.assertRaises(NativeFFIError):
            library.call(NativeSignature("qgf_point_sum", (self.layout,), "f64"),
                         NativeStructValue(self.layout, (2 ** 40, 2.5, 3)))

    def test_reject_invalid_field_count(self):
        library = NativeLibrary(self.path)
        with self.assertRaises(NativeFFIError):
            library.call(NativeSignature("qgf_point_sum", (self.layout,), "f64"),
                         NativeStructValue(self.layout, (1, 2.0)))


if __name__ == "__main__":
    unittest.main()
