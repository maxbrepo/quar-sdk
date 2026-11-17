"""Cycle A/A04: arithmetic type preservation and rejection at the QIR boundary."""
import unittest

from frontend.quar.numeric_types import INTEGER_BITS, integer_range
from frontend.quar.qir.model import QInstruction, QValue
from frontend.quar.qir.operations import QIROperationError, validate_instruction
from frontend.quar.qir.types import canonical_type


class TypedQIRArithmeticA04(unittest.TestCase):
    def test_integer_arithmetic_preserves_exact_width(self):
        """Every integer width accepts same-type arithmetic and comparisons."""
        for name in INTEGER_BITS:
            with self.subTest(type=name):
                qtype = canonical_type(name)
                left, right, result = (QValue(label, qtype) for label in ('left', 'right', 'result'))
                for opcode in ('add', 'sub', 'mul', 'div', 'mod', 'bit_and', 'bit_or', 'bit_xor', 'shl', 'shr'):
                    validate_instruction(QInstruction(opcode, (left, right), result))
                validate_instruction(QInstruction('lt', (left, right), QValue('flag', canonical_type('bool'))))

    def test_mixed_width_arithmetic_is_rejected(self):
        """QIR must not silently promote signedness or integer width."""
        for left_type, right_type in (('i8', 'i16'), ('u8', 'i8'), ('i32', 'u32'), ('i64', 'i128')):
            with self.subTest(left=left_type, right=right_type):
                left = QValue('left', canonical_type(left_type))
                right = QValue('right', canonical_type(right_type))
                result = QValue('result', canonical_type(left_type))
                with self.assertRaises(QIROperationError):
                    validate_instruction(QInstruction('add', (left, right), result))
                with self.assertRaises(QIROperationError):
                    validate_instruction(QInstruction('lt', (left, right), QValue('flag', canonical_type('bool'))))

    def test_constants_respect_integer_boundaries(self):
        """QIR constant validation must reject overflow for every integer type."""
        for name in INTEGER_BITS:
            minimum, maximum = integer_range(name)
            result = QValue('value', canonical_type(name))
            for value in (minimum, maximum):
                with self.subTest(type=name, value=value):
                    validate_instruction(QInstruction('const', (), result, immediate=value))
            for value in (minimum - 1, maximum + 1):
                with self.subTest(type=name, value=value):
                    with self.assertRaises(QIROperationError):
                        validate_instruction(QInstruction('const', (), result, immediate=value))

    def test_result_type_cannot_change_implicitly(self):
        """A correctly typed operand pair cannot produce a different integer type."""
        for name in INTEGER_BITS:
            with self.subTest(type=name):
                source = QValue('source', canonical_type(name))
                target_name = 'i32' if name != 'i32' else 'i64'
                target = QValue('target', canonical_type(target_name))
                with self.assertRaises(QIROperationError):
                    validate_instruction(QInstruction('add', (source, source), target))


if __name__ == '__main__':
    unittest.main()
