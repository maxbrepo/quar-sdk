"""A08: characterize raw QRVM integer arithmetic and missing width enforcement."""
import unittest

from frontend.quar.numeric_types import INTEGER_BITS, integer_range
from qrvm.instructions import OpCode
from qrvm.vm import QRVM


class TypedQRVMOverflowA08(unittest.TestCase):
    def evaluate(self, left, right, opcode):
        vm = QRVM()
        vm.run([(OpCode.PUSH_INT, left), (OpCode.PUSH_INT, right), (opcode, None)])
        return vm.stack[-1]

    def test_raw_addition_exceeds_each_integer_maximum(self):
        # This is a characterization test, NOT an overflow-safety guarantee.
        for type_name in INTEGER_BITS:
            with self.subTest(type_name=type_name):
                _, maximum = integer_range(type_name)
                self.assertEqual(self.evaluate(maximum, 1, OpCode.ADD), maximum + 1)

    def test_raw_subtraction_exceeds_each_integer_minimum(self):
        for type_name in INTEGER_BITS:
            with self.subTest(type_name=type_name):
                minimum, _ = integer_range(type_name)
                self.assertEqual(self.evaluate(minimum, 1, OpCode.SUB), minimum - 1)

    def test_raw_multiplication_exceeds_each_integer_maximum(self):
        for type_name in INTEGER_BITS:
            with self.subTest(type_name=type_name):
                _, maximum = integer_range(type_name)
                self.assertEqual(self.evaluate(maximum, 2, OpCode.MUL), maximum * 2)

    def test_signed_minimum_divided_by_minus_one_is_unbounded(self):
        for type_name, (_, signed) in INTEGER_BITS.items():
            if not signed:
                continue
            with self.subTest(type_name=type_name):
                minimum, maximum = integer_range(type_name)
                result = self.evaluate(minimum, -1, OpCode.DIV)
                self.assertEqual(result, -minimum)
                self.assertGreater(result, maximum)


if __name__ == "__main__":
    unittest.main()
