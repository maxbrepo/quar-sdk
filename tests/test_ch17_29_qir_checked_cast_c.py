"""Compile and execute the supported checked integer cast C adapter."""
import ctypes
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from frontend.quar.qir.c_backend import emit_c_function
from frontend.quar.qir.model import QBlock, QFunction, QInstruction, QReturn, QType, QValue


class CheckedCastCTests(unittest.TestCase):
    def run_cast(self, source_type, target_type, value):
        source = QValue("source", QType(source_type))
        result = QValue("result", QType(target_type))
        function = QFunction("checked_cast", result.type, (source,), (
            QBlock("entry", (QInstruction("cast", (source,), result),), QReturn(result)),
        ))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "cast.c").write_text(emit_c_function(function))
            subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", "-shared", "-fPIC", "cast.c", "-o", "cast.so"], cwd=path, check=True, capture_output=True)
            library = ctypes.CDLL(str(path / "cast.so"))
            library.checked_cast.argtypes = [{"i32": ctypes.c_int32, "i8": ctypes.c_int8, "u8": ctypes.c_uint8, "i16": ctypes.c_int16, "u16": ctypes.c_uint16}[source_type]]
            library.checked_cast.restype = {"i32": ctypes.c_int32, "i8": ctypes.c_int8, "u8": ctypes.c_uint8, "i16": ctypes.c_int16, "u16": ctypes.c_uint16}[target_type]
            return library.checked_cast(value)

    def test_checked_casts_in_range(self):
        for source, target, value in (("i32", "u8", 255), ("i32", "i8", -128), ("i32", "u16", 65535), ("u8", "i32", 255), ("i16", "i32", -32768)):
            with self.subTest(source=source, target=target):
                self.assertEqual(self.run_cast(source, target, value), value)

    def test_out_of_range_cast_emits_abort_guard(self):
        source = QValue("source", QType("i32"))
        result = QValue("result", QType("u8"))
        function = QFunction("checked_cast", result.type, (source,), (
            QBlock("entry", (QInstruction("cast", (source,), result),), QReturn(result)),
        ))
        generated = emit_c_function(function)
        self.assertIn("< 0", generated)
        self.assertIn("> 255", generated)
        self.assertIn("abort();", generated)


if __name__ == "__main__":
    unittest.main()
