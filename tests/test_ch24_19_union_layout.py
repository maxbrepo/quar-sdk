"""Verify generic C union ABI layouts against a compiled native fixture."""

import ctypes
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from qrvm.native_struct_layout import NativeStructLayoutError
from qrvm.native_union_layout import NativeUnionLayout


class NativeUnionLayoutTests(unittest.TestCase):
    def test_layout_matches_compiled_c(self):
        if shutil.which("cc") is None:
            self.skipTest("C compiler not installed")
        fixture = Path(__file__).resolve().parents[1] / "fixtures/qgf_ffi_union_layout.c"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "libunion_layout.so"
            subprocess.run(["cc", "-std=c11", "-shared", "-fPIC", str(fixture), "-o", str(output)],
                           check=True, capture_output=True)
            library = ctypes.CDLL(str(output))
            layout = NativeUnionLayout("QGFNativeUnion", (("signed_value", "i32"),
                                                          ("unsigned_value", "u64"),
                                                          ("decimal_value", "f64")))
            actual = layout.describe()
            for key in ("size", "alignment"):
                function = getattr(library, "qgf_union_" + key)
                function.restype = ctypes.c_size_t
                self.assertEqual(actual[key], function())
            for field, prefix in (("signed_value", "signed"), ("unsigned_value", "unsigned"),
                                  ("decimal_value", "decimal")):
                function = getattr(library, "qgf_union_" + prefix + "_offset")
                function.restype = ctypes.c_size_t
                self.assertEqual(actual["offsets"][field], function())
                self.assertEqual(actual["offsets"][field], 0)

    def test_reject_duplicate_fields(self):
        with self.assertRaises(NativeStructLayoutError):
            NativeUnionLayout("U", (("x", "i32"), ("x", "f64")))

    def test_reject_unknown_field_type(self):
        with self.assertRaises(NativeStructLayoutError):
            NativeUnionLayout("U", (("x", "opaque"),))

    def test_reject_empty_union(self):
        with self.assertRaises(NativeStructLayoutError):
            NativeUnionLayout("U", ())

    def test_reject_invalid_identifiers(self):
        with self.assertRaises(NativeStructLayoutError):
            NativeUnionLayout("Invalid Name", (("x", "i32"),))
        with self.assertRaises(NativeStructLayoutError):
            NativeUnionLayout("U", (("invalid field", "i32"),))

    def test_reject_malformed_field(self):
        with self.assertRaises(NativeStructLayoutError):
            NativeUnionLayout("U", (("x", "i32", "extra"),))


if __name__ == "__main__":
    unittest.main()
