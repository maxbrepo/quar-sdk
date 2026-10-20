"""Tests for the isolated Chapter 15.5 optional-value reference model."""

import unittest

from memory.optional_value import EmptyOptionalError, OptionalValue


class OptionalReferenceModelTests(unittest.TestCase):
    def test_present_integer(self):
        self.assertEqual(OptionalValue.some(42).unwrap(), 42)

    def test_present_false_is_valid(self):
        self.assertIs(OptionalValue.some(False).unwrap(), False)

    def test_present_empty_string_is_valid(self):
        self.assertEqual(OptionalValue.some("").unwrap(), "")

    def test_empty_is_absent(self):
        self.assertFalse(OptionalValue.empty().present)

    def test_unwrap_empty_raises(self):
        with self.assertRaises(EmptyOptionalError):
            OptionalValue.empty().unwrap()

    def test_present_none_rejected(self):
        with self.assertRaises(ValueError):
            OptionalValue.some(None)

    def test_absent_cannot_carry_payload(self):
        with self.assertRaises(ValueError):
            OptionalValue(present=False, value=1)

    def test_immutable_container(self):
        from dataclasses import FrozenInstanceError
        value = OptionalValue.some(1)
        with self.assertRaises(FrozenInstanceError):
            value.present = False


if __name__ == "__main__":
    unittest.main()
