"""Cycle A/A05: exhaustive QIR integer cast range-classification regression."""
import unittest

from frontend.quar.numeric_types import INTEGER_BITS, integer_range as frontend_range
from frontend.quar.qir.cast_safety import assess_integer_cast, integer_range as qir_range
from frontend.quar.qir.model import QInstruction, QValue
from frontend.quar.qir.operations import validate_instruction
from frontend.quar.qir.types import canonical_type


class TypedQIRCastMatrixA05(unittest.TestCase):
    def test_all_integer_ranges_match_frontend(self):
        for name in INTEGER_BITS:
            with self.subTest(type=name):
                self.assertEqual(qir_range(canonical_type(name)), frontend_range(name))

    def test_all_hundred_cast_pairs_classified_by_range_containment(self):
        for source_name in INTEGER_BITS:
            for target_name in INTEGER_BITS:
                with self.subTest(source=source_name, target=target_name):
                    source = canonical_type(source_name)
                    target = canonical_type(target_name)
                    src_min, src_max = frontend_range(source_name)
                    dst_min, dst_max = frontend_range(target_name)
                    assessment = assess_integer_cast(source, target)
                    expected_check = src_min < dst_min or src_max > dst_max
                    self.assertEqual(assessment.requires_runtime_check, expected_check)
                    self.assertEqual((assessment.minimum, assessment.maximum), (dst_min, dst_max))

    def test_explicit_cast_is_well_typed_even_when_runtime_check_needed(self):
        for source_name in INTEGER_BITS:
            for target_name in INTEGER_BITS:
                with self.subTest(source=source_name, target=target_name):
                    source = QValue('source', canonical_type(source_name))
                    target = QValue('target', canonical_type(target_name))
                    validate_instruction(QInstruction('cast', (source,), target))

    def test_known_signed_unsigned_boundary_transitions(self):
        cases = (('u8', 'i16', False), ('i8', 'u8', True),
                 ('u8', 'i8', True), ('i32', 'i64', False),
                 ('u64', 'i128', False), ('i128', 'u128', True),
                 ('u128', 'i128', True), ('u128', 'u128', False))
        for src, dst, requires_check in cases:
            with self.subTest(source=src, target=dst):
                self.assertEqual(
                    assess_integer_cast(canonical_type(src), canonical_type(dst)).requires_runtime_check,
                    requires_check)


if __name__ == '__main__':
    unittest.main()
