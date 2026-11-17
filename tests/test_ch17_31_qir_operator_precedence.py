"""Lock down parser precedence before QIR lowering consumes its AST."""
import unittest

from frontend.quar.ast_nodes import BinaryOperation
from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser


class OperatorPrecedenceTests(unittest.TestCase):
    def parse_expression(self, source):
        return Parser(Lexer(f"x = {source};").tokenize()).parse()[0].value

    def test_precedence_and_left_associativity(self):
        for source, outer, left, right in (
            ("2 + 3 * 4", "+", None, "*"),
            ("(2 + 3) * 4", "*", "+", None),
            ("20 - 6 - 2", "-", "-", None),
            ("1 + 2 << 3", "<<", "+", None),
            ("1 < 2 and 3 < 4", "and", "<", "<"),
            ("1 == 2 or 3 == 4", "or", "==", "=="),
        ):
            with self.subTest(source=source):
                expression = self.parse_expression(source)
                self.assertIsInstance(expression, BinaryOperation)
                self.assertEqual(expression.operator, outer)
                if left is not None:
                    self.assertIsInstance(expression.left, BinaryOperation)
                    self.assertEqual(expression.left.operator, left)
                if right is not None:
                    self.assertIsInstance(expression.right, BinaryOperation)
                    self.assertEqual(expression.right.operator, right)


if __name__ == "__main__":
    unittest.main()
