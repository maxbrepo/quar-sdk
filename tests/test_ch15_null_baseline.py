"""Chapter 15.4: guard against assuming unimplemented null syntax exists."""

import unittest

from frontend.quar.tokens import TokenType


class NullBaselineTests(unittest.TestCase):
    def test_boolean_literals_are_explicit(self):
        self.assertIn("TRUE", TokenType.__members__)
        self.assertIn("FALSE", TokenType.__members__)

    def test_null_literal_is_not_yet_defined(self):
        for name in ("NULL", "NIL", "NONE"):
            with self.subTest(name=name):
                self.assertNotIn(name, TokenType.__members__)

    def test_ownership_keywords_are_not_yet_defined(self):
        for name in ("BORROW", "MOVE", "UNSAFE"):
            with self.subTest(name=name):
                self.assertNotIn(name, TokenType.__members__)


if __name__ == "__main__":
    unittest.main()
