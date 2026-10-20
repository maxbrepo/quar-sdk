"""Tests for the experimental canonical optional type spelling."""
import unittest

from memory.optional_type_syntax import (
    OptionalSyntaxError, format_optional_type, parse_optional_type,
)
from memory.optional_types import ValueType


class OptionalTypeSyntaxTests(unittest.TestCase):
    def test_primitive_optional(self):
        self.assertEqual(parse_optional_type('int?'), ValueType('int', True))

    def test_primitive_nonoptional(self):
        self.assertEqual(parse_optional_type('int'), ValueType('int'))

    def test_named_type_optional(self):
        self.assertEqual(parse_optional_type('Widget?'), ValueType('Widget', True))

    def test_round_trip(self):
        for value in (ValueType('bool'), ValueType('string', True), ValueType('_Node2', True)):
            self.assertEqual(parse_optional_type(format_optional_type(value)), value)

    def test_double_optional_is_not_canonical(self):
        with self.assertRaises(OptionalSyntaxError):
            parse_optional_type('int??')

    def test_whitespace_is_not_canonical(self):
        for spelling in (' int?', 'int? ', 'int ?'):
            with self.subTest(spelling=spelling), self.assertRaises(OptionalSyntaxError):
                parse_optional_type(spelling)

    def test_missing_type_rejected(self):
        for spelling in ('', '?'):
            with self.subTest(spelling=spelling), self.assertRaises(OptionalSyntaxError):
                parse_optional_type(spelling)

    def test_no_confusion_between_presence_and_value(self):
        self.assertNotEqual(parse_optional_type('int'), parse_optional_type('int?'))


if __name__ == '__main__':
    unittest.main()
