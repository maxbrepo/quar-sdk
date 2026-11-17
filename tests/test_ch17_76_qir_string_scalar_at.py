"""Exercise indexed Unicode scalar reads in the QIR C backend."""
import ctypes
from pathlib import Path
import subprocess
import tempfile
import unittest

from frontend.quar.qir.c_backend import emit_c_function
from frontend.quar.qir.model import QBlock, QFunction, QInstruction, QMetadata, QReturn, QSafetyMetadata, QType, QValue
from frontend.quar.qir.operations import QIROperationError, validate_instruction


class CString(ctypes.Structure):
    _fields_ = [("data", ctypes.POINTER(ctypes.c_uint8)), ("length", ctypes.c_size_t)]


class ScalarAtTests(unittest.TestCase):
    def test_scalar_at_compiled(self):
        text = QValue("text", QType("string"))
        position = QValue("position", QType("i32"))
        result = QValue("scalar", QType("i32"))
        metadata = QMetadata(safety=QSafetyMetadata(checks=("string_length", "bounds")))
        instruction = QInstruction("string_scalar_at", (text, position), result, metadata=metadata)
        function = QFunction("scalar_at", QType("i32"), (text, position), (
            QBlock("entry", (instruction,), QReturn(result)),
        ))
        source = emit_c_function(function)
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "module.c").write_text(source, encoding="utf-8")
            subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", "-shared", "-fPIC", "module.c", "-o", "module.so"], cwd=folder, check=True, capture_output=True)
            library = ctypes.CDLL(str(folder / "module.so"))
            library.scalar_at.argtypes = [CString, ctypes.c_int32]
            library.scalar_at.restype = ctypes.c_int32
            for sample in ("abc", "aé😀", "e\u0301", "a\x00b"):
                data = sample.encode("utf-8")
                buffer = (ctypes.c_uint8 * len(data))(*data)
                for index, character in enumerate(sample):
                    with self.subTest(sample=sample, index=index):
                        self.assertEqual(library.scalar_at(CString(buffer, len(data)), index), ord(character))

    def test_requires_bounds_and_length_checks(self):
        text = QValue("text", QType("string"))
        index = QValue("index", QType("i32"))
        result = QValue("result", QType("i32"))
        for checks in ((), ("bounds",), ("string_length",)):
            instruction = QInstruction("string_scalar_at", (text, index), result,
                                       metadata=QMetadata(safety=QSafetyMetadata(checks=checks)))
            with self.subTest(checks=checks), self.assertRaises(QIROperationError):
                validate_instruction(instruction)


if __name__ == "__main__":
    unittest.main()
