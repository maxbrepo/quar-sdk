"""Check nested C struct/union/array ABI layouts against a compiled fixture."""
import ctypes
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from qrvm.native_composite_layout import NativeArrayType, NativeCompositeLayout
from qrvm.native_struct_layout import NativeStructLayoutError


class CompositeLayoutTests(unittest.TestCase):
    def setUp(self):
        self.point = NativeCompositeLayout("Point", "struct", (("x", "i32"), ("y", "f64")))
        self.number = NativeCompositeLayout("Number", "union", (("bits", "u64"), ("value", "f64")))
        self.packet = NativeCompositeLayout("Packet", "struct", (
            ("tag", "u32"), ("points", NativeArrayType(self.point, 3)),
            ("number", self.number), ("samples", NativeArrayType("i32", 4)),
        ))

    def test_layout_matches_compiled_c(self):
        if shutil.which("cc") is None:
            self.skipTest("C compiler unavailable")
        fixture = Path(__file__).resolve().parents[1] / "fixtures/qgf_ffi_composite_layout.c"
        with tempfile.TemporaryDirectory() as folder:
            library_path = Path(folder) / "libcomposite.so"
            subprocess.run(["cc", "-std=c11", "-shared", "-fPIC", str(fixture), "-o", str(library_path)],
                           check=True, capture_output=True)
            library = ctypes.CDLL(str(library_path))
            actual = self.packet.describe()
            for property_name in ("size", "alignment"):
                function = getattr(library, f"qgf_packet_{property_name}")
                function.restype = ctypes.c_size_t
                self.assertEqual(actual[property_name], function())
            for field_name, offset in actual["offsets"].items():
                function = getattr(library, f"qgf_packet_{field_name}_offset")
                function.restype = ctypes.c_size_t
                self.assertEqual(offset, function())
            for name, layout in (("point", self.point), ("number", self.number)):
                function = getattr(library, f"qgf_{name}_size")
                function.restype = ctypes.c_size_t
                self.assertEqual(layout.describe()["size"], function())

    def test_union_fields_overlap(self):
        self.assertEqual(set(self.number.describe()["offsets"].values()), {0})

    def test_reject_invalid_array_lengths(self):
        for length in (0, -1, True, 65537, 1.5):
            with self.subTest(length=length), self.assertRaises(NativeStructLayoutError):
                NativeArrayType("i32", length)

    def test_reject_unsupported_field_types(self):
        with self.assertRaises(NativeStructLayoutError):
            NativeArrayType("opaque", 2)
        with self.assertRaises(NativeStructLayoutError):
            NativeCompositeLayout("X", "struct", (("ptr", ctypes.c_void_p),))

    def test_reject_duplicate_fields(self):
        with self.assertRaises(NativeStructLayoutError):
            NativeCompositeLayout("X", "struct", (("x", "i32"), ("x", "u32")))

    def test_reject_invalid_declarations(self):
        for name, kind, fields in (("Bad Name", "struct", (("x", "i32"),)),
                                   ("X", "class", (("x", "i32"),)),
                                   ("X", "union", ()),
                                   ("X", "struct", (("x", "i32", "extra"),))):
            with self.subTest(name=name, kind=kind, fields=fields), self.assertRaises(NativeStructLayoutError):
                NativeCompositeLayout(name, kind, fields)


if __name__ == "__main__":
    unittest.main()
