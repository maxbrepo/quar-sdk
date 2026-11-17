"""Executable C adapter tests for the initial fixed-size i32 array subset."""
import ctypes
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from frontend.quar.qir.c_backend import QIRCBackendError, emit_c_function
from frontend.quar.qir.model import QBlock, QFunction, QInstruction, QMetadata, QReturn, QSafetyMetadata, QType, QValue

I32 = QType("i32")
PTR = QType("ptr<i32>")
BOUNDS = QMetadata(safety=QSafetyMetadata(checks=("bounds",)))


def make_function(index=1):
    array = QValue("array", PTR)
    idx = QValue("idx", I32)
    value = QValue("value", I32)
    result = QValue("result", I32)
    instructions = (
        QInstruction("array_alloc", result=array, immediate=3),
        QInstruction("const", result=idx, immediate=index),
        QInstruction("const", result=value, immediate=37),
        QInstruction("array_set", operands=(array, idx, value), metadata=BOUNDS),
        QInstruction("array_get", operands=(array, idx), result=result, metadata=BOUNDS),
    )
    return QFunction("array_demo", I32, (), (QBlock("entry", instructions, QReturn(result)),))


class ArrayCBackendTests(unittest.TestCase):
    def test_generated_c_executes_array_write_and_read(self):
        source = emit_c_function(make_function())
        with tempfile.TemporaryDirectory() as tmp:
            c_path = Path(tmp) / "demo.c"
            so_path = Path(tmp) / "demo.so"
            c_path.write_text(source)
            subprocess.run(["cc", "-std=c99", "-shared", "-fPIC", str(c_path), "-o", str(so_path)], check=True, capture_output=True)
            library = ctypes.CDLL(str(so_path))
            self.assertEqual(library.array_demo(), 37)

    def test_negative_index_traps_before_memory_access(self):
        source = emit_c_function(make_function(-1))
        with tempfile.TemporaryDirectory() as tmp:
            c_path = Path(tmp) / "demo.c"
            exe_path = Path(tmp) / "demo"
            c_path.write_text(source + "\nint main(void) { return array_demo(); }\n")
            subprocess.run(["cc", "-std=c99", str(c_path), "-o", str(exe_path)], check=True, capture_output=True)
            result = subprocess.run([str(exe_path)], capture_output=True, cwd=tmp)
            self.assertNotEqual(result.returncode, 0)

    def test_pointer_parameter_is_not_accepted_as_local_array(self):
        array = QValue("external", PTR)
        index = QValue("index", I32)
        result = QValue("result", I32)
        function = QFunction("external_array", I32, (array, index), (
            QBlock("entry", (QInstruction("array_get", (array, index), result, metadata=BOUNDS),), QReturn(result)),
        ))
        with self.assertRaises(QIRCBackendError):
            emit_c_function(function)


if __name__ == "__main__":
    unittest.main()
