"""Exercise explicit native resource release and rejected stale handles."""
import subprocess
import tempfile
import unittest
from pathlib import Path

from qrvm.native_ffi import NativeFFIError, NativeLibrary, NativeSignature


class NativeLifetimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.path = Path(cls.temp.name) / "liblifetime.so"
        source = Path(__file__).resolve().parents[1] / "fixtures" / "qgf_ffi_lifetime.c"
        subprocess.run(["cc", "-shared", "-fPIC", str(source), "-o", str(cls.path)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.library = NativeLibrary(self.path)
        self.create = NativeSignature("qgf_create_handle", (), "opaque")
        self.read = NativeSignature("qgf_read_allocated", ("opaque",), "i32")
        self.destroy = NativeSignature("qgf_destroy_handle", ("opaque",), "void")

    def test_create_read_release(self):
        handle = self.library.call(self.create)
        self.assertEqual(self.library.call(self.read, handle), 42)
        self.library.release_handle(handle, self.destroy)
        with self.assertRaisesRegex(NativeFFIError, "released"):
            self.library.call(self.read, handle)

    def test_double_release_rejected(self):
        handle = self.library.call(self.create)
        self.library.release_handle(handle, self.destroy)
        with self.assertRaisesRegex(NativeFFIError, "already been released"):
            self.library.release_handle(handle, self.destroy)

    def test_foreign_handle_rejected(self):
        foreign = NativeLibrary(self.path)
        handle = foreign.call(self.create)
        with self.assertRaises(NativeFFIError):
            self.library.release_handle(handle, self.destroy)
        foreign.release_handle(handle, self.destroy)

    def test_invalid_destructor_does_not_release(self):
        handle = self.library.call(self.create)
        with self.assertRaisesRegex(NativeFFIError, "destructor"):
            self.library.release_handle(handle, self.read)
        self.assertEqual(self.library.call(self.read, handle), 42)
        self.library.release_handle(handle, self.destroy)


if __name__ == "__main__":
    unittest.main()
