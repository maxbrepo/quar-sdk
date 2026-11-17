"""Regression checks for exact integer division in the QRVM."""
import unittest

from qrvm.instructions import OpCode
from qrvm.vm import QRVM


class TypedQRVMExactDivisionA06(unittest.TestCase):
    def evaluate(self, left, right):
        vm = QRVM()
        vm.run([(OpCode.PUSH_INT, left), (OpCode.PUSH_INT, right), (OpCode.DIV, None)])
        return vm.stack[-1]

    def test_large_signed_and_unsigned_values(self):
        for value in (2**63 - 1, 2**64 - 1, 2**127 - 1, 2**128 - 1):
            with self.subTest(value=value):
                self.assertEqual(self.evaluate(value, 3), value // 3)

    def test_truncates_toward_zero(self):
        for left, right, expected in ((-7, 3, -2), (7, -3, -2), (-7, -3, 2), (-1, 3, 0)):
            with self.subTest(left=left, right=right):
                self.assertEqual(self.evaluate(left, right), expected)

    def test_zero_division_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "Division by zero"):
            self.evaluate(5, 0)

    def test_float_division_unchanged(self):
        vm = QRVM()
        vm.run([(OpCode.PUSH_DOUBLE, 7.0), (OpCode.PUSH_DOUBLE, 2.0), (OpCode.DIV, None)])
        self.assertEqual(vm.stack[-1], 3.5)


if __name__ == "__main__":
    unittest.main()
