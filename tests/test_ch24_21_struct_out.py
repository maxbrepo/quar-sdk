"""Verify a C function writing into an adapter-owned output structure."""
import subprocess
import tempfile
import unittest
from pathlib import Path

from qrvm.native_ffi import NativeFFIError, NativeLibrary, NativeSignature, NativeStructValue
from qrvm.native_struct_layout import NativeStructLayout


class NativeStructOutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        source = Path(__file__).resolve().parents[1] / "fixtures/qgf_ffi_struct_out.c"
        cls.library_path = Path(cls.directory.name) / "libstruct_out.so"
        subprocess.run(["cc", "-std=c11", "-shared", "-fPIC", str(source), "-o", str(cls.library_path)],
                       check=True, capture_output=True)
        cls.layout = NativeStructLayout("QGFOutPoint", (("x", "i32"), ("y", "f64"), ("flags", "u32")))

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def test_successful_output(self):
        status, point = NativeLibrary(self.library_path).call_struct_out("qgf_fill_point", self.layout)
        self.assertEqual(status, 0)
        self.assertEqual(point, NativeStructValue(self.layout, (20, 2.5, 3)))

    def test_failed_output_does_not_escape(self):
        with self.assertRaisesRegex(NativeFFIError, "status 7"):
            NativeLibrary(self.library_path).call_struct_out("qgf_fail_point", self.layout)

    def test_invalid_layout_rejected(self):
        with self.assertRaises(NativeFFIError):
            NativeLibrary(self.library_path).call_struct_out("qgf_fill_point", "QGFOutPoint")

    def test_missing_symbol_rejected(self):
        with self.assertRaises(NativeFFIError):
            NativeLibrary(self.library_path).call_struct_out("qgf_missing", self.layout)

    def test_invalid_symbol_rejected(self):
        with self.assertRaises(NativeFFIError):
            NativeLibrary(self.library_path).call_struct_out("bad-name", self.layout)


if __name__ == "__main__":
    unittest.main()
