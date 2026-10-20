import unittest
from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from qrvm.inspector_ast_locations import node_source_range


class ParserSourceSpanTests(unittest.TestCase):
    def parse(self, source):
        return Parser(Lexer(source).tokenize()).parse()

    def test_statement_has_coordinates(self):
        node = self.parse("int x = 42;\n")[0]
        self.assertEqual(node.start, (1, 1))
        self.assertGreater(node.end[1], node.start[1])

    def test_multiline_statements(self):
        nodes = self.parse("int a = 1;\nint b = 2;\n")
        self.assertEqual(nodes[1].start[0], 2)

    def test_bridge_reads_parser_coordinates(self):
        node = self.parse("int x = 42;\n")[0]
        self.assertIsNotNone(node_source_range(node, "demo.vq"))

    def test_expression_coordinates(self):
        node = self.parse("int x = 2 + 3;\n")[0]
        self.assertEqual(node.value.start[0], 1)


if __name__ == "__main__":
    unittest.main()
