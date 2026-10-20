"""Chapter 15.10: conservative optional assignment compatibility."""
import unittest

from frontend.quar.semantic import SemanticAnalyzer


class OptionalSemanticTests(unittest.TestCase):
    def setUp(self):
        self.analyzer = SemanticAnalyzer()

    def test_plain_to_optional(self):
        self.assertTrue(self.analyzer.types_compatible('int?', 'int'))

    def test_optional_to_same_optional(self):
        self.assertTrue(self.analyzer.types_compatible('int?', 'int?'))

    def test_optional_to_plain_rejected(self):
        self.assertFalse(self.analyzer.types_compatible('int', 'int?'))

    def test_mismatched_base_types_rejected(self):
        self.assertFalse(self.analyzer.types_compatible('string?', 'int'))

    def test_optional_to_other_optional_rejected(self):
        self.assertFalse(self.analyzer.types_compatible('string?', 'int?'))

    def test_plain_compatibility_unchanged(self):
        self.assertTrue(self.analyzer.types_compatible('int', 'int'))
        self.assertFalse(self.analyzer.types_compatible('string', 'int'))


if __name__ == '__main__':
    unittest.main()
