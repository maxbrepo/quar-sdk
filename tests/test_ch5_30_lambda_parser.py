"""Experimental lambda parsing tests; runtime support is not yet available."""
import unittest
from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from frontend.quar.ast_nodes import LambdaExpression, ReturnStatement
from frontend.quar.errors import ParserError


def parse_lambda(source: str) -> LambdaExpression:
    """Parse one lambda expression and return its AST node."""
    parser = Parser(Lexer(source).tokenize())
    node = parser.parse_expression()
    parser.expect(type(parser.current().type).EOF)
    return node


class LambdaParserTests(unittest.TestCase):
    def test_one_parameter(self):
        node = parse_lambda('lambda(int x)->int { return x; }')
        self.assertEqual(node.parameters[0].name, 'x')
        self.assertEqual(node.return_type, 'int')
        self.assertIsInstance(node.body[0], ReturnStatement)

    def test_zero_parameter_void(self):
        node = parse_lambda('lambda()->void { }')
        self.assertEqual(node.parameters, [])
        self.assertEqual(node.body, [])

    def test_multiple_parameters(self):
        node = parse_lambda('lambda(int a, int b)->int { return a + b; }')
        self.assertEqual([p.name for p in node.parameters], ['a', 'b'])

    def test_missing_return_type_rejected(self):
        with self.assertRaises(ParserError):
            parse_lambda('lambda(int x) { return x; }')


if __name__ == '__main__':
    unittest.main()
