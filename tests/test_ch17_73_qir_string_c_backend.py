"""Compile and execute QIR UTF-8 length operations through the C adapter."""
import ctypes
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from frontend.quar.qir.c_backend import emit_c_function
from frontend.quar.qir.model import QBlock, QFunction, QInstruction, QMetadata, QReturn, QSafetyMetadata, QType, QValue


class CString(ctypes.Structure):
    _fields_ = [("data", ctypes.POINTER(ctypes.c_uint8)), ("length", ctypes.c_size_t)]


class StringBackendTests(unittest.TestCase):
    def test_unicode_byte_and_scalar_lengths(self):
        for opcode in ("string_byte_len", "string_scalar_len"):
            with self.subTest(opcode=opcode):
                text = QValue("text", QType("string"))
                result = QValue("length", QType("i32"))
                metadata = QMetadata(safety=QSafetyMetadata(checks=("string_length",)))
                function = QFunction("measure", QType("i32"), (text,), (
                    QBlock("entry", (QInstruction(opcode, (text,), result, metadata=metadata),), QReturn(result)),
                ))
                source = emit_c_function(function)
                with tempfile.TemporaryDirectory() as temp:
                    path = Path(temp)
                    (path / "module.c").write_text(source)
                    subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-shared", "-fPIC", "module.c", "-o", "module.so"], cwd=path, check=True, capture_output=True)
                    library = ctypes.CDLL(str(path / "module.so"))
                    library.measure.argtypes = [CString]
                    library.measure.restype = ctypes.c_int32
                    for sample in ("", "abc", "aé😀", "e\u0301", "a\x00b"):
                        data = sample.encode("utf-8")
                        buffer = (ctypes.c_uint8 * max(1, len(data)))(*data)
                        expected = len(data) if opcode == "string_byte_len" else len(sample)
                        self.assertEqual(library.measure(CString(buffer, len(data))), expected)


if __name__ == "__main__":
    unittest.main()
