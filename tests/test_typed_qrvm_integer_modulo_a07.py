"""Regression tests for integer remainder parity with C semantics."""
import unittest

from qrvm.instructions import OpCode
from qrvm.vm import QRVM


class TypedQRVMIntegerModuloA07(unittest.TestCase):
    def evaluate(self, left, right):
        vm = QRVM()
        vm.run([(OpCode.PUSH_INT, left), (OpCode.PUSH_INT, right), (OpCode.MOD, None)])
        return vm.stack[-1]

    def test_signed_remainder_truncates_quotient_toward_zero(self):
        cases = ((-7, 3, -1), (7, -3, 1), (-7, -3, -1), (7, 3, 1), (-1, 3, -1))
        for left, right, expected in cases:
            with self.subTest(left=left, right=right):
                self.assertEqual(self.evaluate(left, right), expected)

    def test_large_integer_remainder_is_exact(self):
        for value in (2**63 - 1, 2**64 - 1, 2**127 - 1, 2**128 - 1):
            with self.subTest(value=value):
                self.assertEqual(self.evaluate(value, 3), value % 3)
                self.assertEqual(self.evaluate(-value, 3), -(value % 3))

    def test_modulo_by_zero_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "Modulo by zero"):
            self.evaluate(5, 0)

    def test_floating_modulo_unchanged(self):
        vm = QRVM()
        vm.run([(OpCode.PUSH_DOUBLE, 7.5), (OpCode.PUSH_DOUBLE, 2.0), (OpCode.MOD, None)])
        self.assertEqual(vm.stack[-1], 1.5)


if __name__ == "__main__":
    unittest.main()
