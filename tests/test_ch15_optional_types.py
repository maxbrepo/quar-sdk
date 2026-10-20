"""Regression tests for the experimental Chapter 15.6 optional type rules."""
import unittest
from memory.optional_types import (
    FlowValue, OptionalTypeError, Presence, ValueType, can_assign, join_presence,
)


class OptionalTypeRulesTests(unittest.TestCase):
    def test_non_optional_read(self):
        self.assertEqual(FlowValue(ValueType('int')).read(), ValueType('int'))

    def test_unknown_optional_read_rejected(self):
        with self.assertRaises(OptionalTypeError):
            FlowValue(ValueType('int', True)).read()

    def test_checked_optional_read(self):
        value = FlowValue(ValueType('int', True)).checked_present()
        self.assertEqual(value.read(), ValueType('int'))

    def test_known_absent_read_rejected(self):
        with self.assertRaises(OptionalTypeError):
            FlowValue(ValueType('int', True), Presence.ABSENT).read()

    def test_absent_non_optional_rejected(self):
        with self.assertRaises(OptionalTypeError):
            FlowValue(ValueType('int'), Presence.ABSENT)

    def test_optional_assignment_rules(self):
        self.assertTrue(can_assign(ValueType('int'), ValueType('int', True)))
        self.assertFalse(can_assign(ValueType('int', True), ValueType('int')))
        self.assertFalse(can_assign(ValueType('string'), ValueType('int', True)))

    def test_branch_join_conservative(self):
        self.assertEqual(join_presence(Presence.PRESENT, Presence.ABSENT), Presence.UNKNOWN)
        self.assertEqual(join_presence(Presence.PRESENT, Presence.PRESENT), Presence.PRESENT)

    def test_refinement_does_not_mutate_original(self):
        original = FlowValue(ValueType('string', True))
        original.checked_present()
        self.assertEqual(original.presence, Presence.UNKNOWN)

    def test_empty_type_name_rejected(self):
        with self.assertRaises(ValueError):
            ValueType(' ')


if __name__ == '__main__':
    unittest.main()
