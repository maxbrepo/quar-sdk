"""Check opaque pointer transport without permitting arbitrary raw addresses."""
import subprocess
import tempfile
import unittest
from pathlib import Path

from qrvm.native_ffi import NativeFFIError, NativeLibrary, NativeSignature, OpaqueNativePointer


class OpaqueBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        source = Path(__file__).resolve().parents[1] / "fixtures" / "qgf_ffi_opaque.c"
        cls.path = Path(cls.temp.name) / "libopaque.so"
        subprocess.run(["cc", "-shared", "-fPIC", str(source), "-o", str(cls.path)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_roundtrip(self):
        library = NativeLibrary(self.path)
        handle = library.call(NativeSignature("qgf_get_handle", (), "opaque"))
        self.assertIsInstance(handle, OpaqueNativePointer)
        self.assertEqual(library.call(NativeSignature("qgf_read_handle", ("opaque",), "i32"), handle), 42)

    def test_reject_arbitrary_integer(self):
        library = NativeLibrary(self.path)
        with self.assertRaises(NativeFFIError):
            library.call(NativeSignature("qgf_read_handle", ("opaque",), "i32"), 12345)

    def test_reject_cross_library_handle(self):
        first, second = NativeLibrary(self.path), NativeLibrary(self.path)
        handle = first.call(NativeSignature("qgf_get_handle", (), "opaque"))
        with self.assertRaises(NativeFFIError):
            second.call(NativeSignature("qgf_read_handle", ("opaque",), "i32"), handle)

    def test_reject_null_pointer(self):
        library = NativeLibrary(self.path)
        with self.assertRaisesRegex(NativeFFIError, "null opaque pointer"):
            library.call(NativeSignature("qgf_null_handle", (), "opaque"))


if __name__ == "__main__":
    unittest.main()
