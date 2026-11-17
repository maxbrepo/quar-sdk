"""Verify safe output buffers for nested native composite layouts."""
import ctypes
import subprocess
import tempfile
import unittest
from pathlib import Path

from qrvm.native_composite_layout import NativeArrayType, NativeCompositeLayout
from qrvm.native_ffi import NativeFFIError, NativeLibrary


class CompositeOutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        root = Path(__file__).resolve().parents[1]
        cls.library_path = Path(cls.directory.name) / "libcomposite_out.so"
        subprocess.run(["cc", "-std=c11", "-shared", "-fPIC", str(root / "fixtures/qgf_ffi_composite_out.c"), "-o", str(cls.library_path)], check=True, capture_output=True)
        point = NativeCompositeLayout("OutPoint", "struct", (("x", "i32"), ("y", "f64")))
        number = NativeCompositeLayout("OutNumber", "union", (("bits", "u64"), ("value", "f64")))
        cls.layout = NativeCompositeLayout("OutPacket", "struct", (("tag", "u32"), ("points", NativeArrayType(point, 3)), ("number", number), ("samples", NativeArrayType("i32", 4))))

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def test_output_matches_native_layout(self):
        status, raw = NativeLibrary(self.library_path).call_composite_out("qgf_fill_packet", self.layout)
        self.assertEqual(status, 0)
        self.assertIs(type(raw), bytes)
        self.assertEqual(len(raw), self.layout.describe()["size"])
        packet = self.layout.ctypes_type().from_buffer_copy(raw)
        self.assertEqual(packet.tag, 42)
        self.assertEqual(packet.points[0].x, 7)
        self.assertEqual(packet.points[0].y, 2.5)
        self.assertEqual(packet.number.bits, 0x1122334455667788)
        self.assertEqual(packet.samples[0], -3)

    def test_failure_does_not_return_partial_output(self):
        with self.assertRaisesRegex(NativeFFIError, "status 7"):
            NativeLibrary(self.library_path).call_composite_out("qgf_fail_packet", self.layout)

    def test_wrong_layout_rejected(self):
        with self.assertRaises(NativeFFIError):
            NativeLibrary(self.library_path).call_composite_out("qgf_fill_packet", "Packet")

    def test_conflicting_layout_rejected(self):
        library = NativeLibrary(self.library_path)
        library.call_composite_out("qgf_fill_packet", self.layout)
        different = NativeCompositeLayout("Different", "struct", (("x", "i32"),))
        with self.assertRaisesRegex(NativeFFIError, "different ABI"):
            library.call_composite_out("qgf_fill_packet", different)

    def test_missing_symbol_rejected(self):
        with self.assertRaisesRegex(NativeFFIError, "not found"):
            NativeLibrary(self.library_path).call_composite_out("missing_symbol", self.layout)

    def test_invalid_symbol_rejected(self):
        with self.assertRaises(NativeFFIError):
            NativeLibrary(self.library_path).call_composite_out("bad-symbol", self.layout)


if __name__ == "__main__":
    unittest.main()
