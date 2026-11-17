"""Validate the original C ABI declaration syntax and semantic registration."""
import unittest

from frontend.quar.ast_nodes import ExternalFunctionDeclaration
from frontend.quar.errors import ParserError
from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from frontend.quar.semantic import SemanticAnalyzer


def parse(source: str):
    return Parser(Lexer(source).tokenize()).parse()


class ExternalDeclarationTests(unittest.TestCase):
    def test_scalar_declaration(self):
        node = parse('extern "C" i32 qgf_add(i32 a, i32 b);')[0]
        self.assertIsInstance(node, ExternalFunctionDeclaration)
        self.assertEqual((node.abi, node.return_type, node.name), ('C', 'i32', 'qgf_add'))
        self.assertEqual([p.var_type for p in node.parameters], ['i32', 'i32'])

    def test_zero_arguments(self):
        self.assertEqual(parse('extern "C" u32 read_value();')[0].parameters, [])

    def test_reject_other_abi(self):
        with self.assertRaises(ParserError):
            parse('extern "Rust" i32 foo();')

    def test_reject_unsupported_return_type(self):
        with self.assertRaises(ParserError):
            parse('extern "C" string foo();')

    def test_reject_default_arguments(self):
        with self.assertRaises(ParserError):
            parse('extern "C" i32 foo(i32 a = 3);')

    def test_reject_duplicate_parameter(self):
        with self.assertRaises(ParserError):
            parse('extern "C" i32 foo(i32 a, i32 a);')

    def test_semantic_accepts_declared_external(self):
        program = parse('extern "C" i32 qgf_add(i32 a, i32 b);')
        self.assertIsNotNone(SemanticAnalyzer().analyze(program))


if __name__ == '__main__':
    unittest.main()
