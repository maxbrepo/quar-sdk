"""Compile and execute the initial QIR-to-C adapter with the system C compiler."""
import ctypes
import os
import shutil
import subprocess
import tempfile
import unittest

from frontend.quar.qir.c_backend import QIRCBackendError, emit_c_function
from frontend.quar.qir.model import QBlock, QFunction, QInstruction, QMetadata, QReturn, QSafetyMetadata, QType, QValue

I = QType("i32")


def make_function(instructions, parameters=(), result=None, name="qir_test"):
    return QFunction(name, I, tuple(parameters),
                     (QBlock("entry", tuple(instructions), QReturn(result or instructions[-1].result)),))


class CBackendTests(unittest.TestCase):
    def run_c(self, function, arguments=()):
        if shutil.which("cc") is None:
            self.skipTest("C compiler not installed")
        with tempfile.TemporaryDirectory() as folder:
            source = os.path.join(folder, "qir.c")
            shared = os.path.join(folder, "qir.so")
            with open(source, "w", encoding="utf-8") as handle:
                handle.write(emit_c_function(function))
            subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", "-shared", "-fPIC", source, "-o", shared], check=True, capture_output=True)
            lib = ctypes.CDLL(shared)
            method = getattr(lib, function.name)
            method.argtypes = [ctypes.c_int32] * len(arguments)
            method.restype = ctypes.c_int32
            return method(*arguments)

    def test_constant(self):
        v = QValue("v", I)
        self.assertEqual(self.run_c(make_function([QInstruction("const", (), v, 42)])), 42)

    def test_negative_constant(self):
        v = QValue("v", I)
        self.assertEqual(self.run_c(make_function([QInstruction("const", (), v, -2147483648)])), -2147483648)

    def test_copy_parameter(self):
        p, v = QValue("p", I), QValue("v", I)
        self.assertEqual(self.run_c(make_function([QInstruction("copy", (p,), v)], (p,)), (-7,)), -7)

    def test_arithmetic(self):
        a, b, c, d, e = (QValue(x, I) for x in "abcde")
        fn = make_function([QInstruction("const", (), a, 6), QInstruction("const", (), b, 7),
                            QInstruction("mul", (a, b), c), QInstruction("sub", (c, a), d),
                            QInstruction("add", (d, b), e)])
        self.assertEqual(self.run_c(fn), 43)

    def test_reject_safety_obligation(self):
        v = QValue("v", I)
        fn = make_function([QInstruction("const", (), v, 1, QMetadata(safety=QSafetyMetadata(checks=("overflow",))))])
        with self.assertRaises(QIRCBackendError):
            emit_c_function(fn)

    def test_reject_unsupported_type(self):
        v = QValue("v", QType("i64"))
        fn = QFunction("qir_test", v.type, (), (QBlock("entry", (QInstruction("const", (), v, 1),), QReturn(v)),))
        with self.assertRaises(QIRCBackendError):
            emit_c_function(fn)

    def test_division_and_modulo(self):
        a, b, out = (QValue(x, I) for x in "abc")
        for op, expected in (("div", -2), ("mod", -1)):
            with self.subTest(op=op):
                fn = make_function([QInstruction(op, (a, b), out)], (a, b))
                self.assertEqual(self.run_c(fn, (-7, 3)), expected)

    def test_comparisons_return_bool(self):
        a, b = QValue("a", I), QValue("b", I)
        result = QValue("result", QType("bool"))
        for op, expected in (("eq", 0), ("ne", 1), ("lt", 1), ("le", 1), ("gt", 0), ("ge", 0)):
            with self.subTest(op=op):
                fn = QFunction("qir_test", result.type, (a, b),
                    (QBlock("entry", (QInstruction(op, (a, b), result),), QReturn(result)),))
                self.assertEqual(self.run_c(fn, (2, 3)), expected)

    def test_bitwise_and_shifts(self):
        a, b, out = (QValue(x, I) for x in "abc")
        cases = (
            ("bit_and", -1, 6, 6),
            ("bit_or", -8, 3, -5),
            ("bit_xor", -1, 3, -4),
            ("shl", -1, 1, -2),
            ("shl", 1, 31, -2147483648),
            ("shr", -7, 1, -4),
            ("shr", -1, 31, -1),
            ("shr", 8, 2, 2),
            ("shr", -7, 0, -7),
        )
        for op, left, right, expected in cases:
            with self.subTest(op=op, left=left, right=right):
                fn = make_function([QInstruction(op, (a, b), out)], (a, b))
                self.assertEqual(self.run_c(fn, (left, right)), expected)
        fn = make_function([QInstruction("bit_not", (a,), out)], (a,))
        self.assertEqual(self.run_c(fn, (0,)), -1)
        self.assertEqual(self.run_c(fn, (-1,)), 0)

    def test_reject_unsupported_opcode(self):
        a, b, c = (QValue(x, I) for x in "abc")
        fn = make_function([QInstruction("const", (), a, 8), QInstruction("const", (), b, 2), QInstruction("cast", (a,), c)])
        # Casts within the supported integer subset are now executable.
        self.assertIn("(int32_t)", emit_c_function(fn))
        with self.assertRaises(QIRCBackendError):
            emit_c_function(make_function([QInstruction("cast", (QValue("wide", QType("i64")),), c)], (QValue("wide", QType("i64")),)))

    def test_reject_invalid_name(self):
        v = QValue("v", I)
        with self.assertRaises(QIRCBackendError):
            emit_c_function(make_function([QInstruction("const", (), v, 1)], name="bad-name"))

    def test_deterministic_and_immutable(self):
        v = QValue("v", I)
        fn = make_function([QInstruction("const", (), v, 1)])
        before = repr(fn)
        self.assertEqual(emit_c_function(fn), emit_c_function(fn))
        self.assertEqual(repr(fn), before)


if __name__ == "__main__":
    unittest.main()
