"""Validate C struct declaration metadata without enabling struct calls."""
import unittest
from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from frontend.quar.semantic import SemanticAnalyzer
from frontend.quar.errors import ParserError, SemanticError
from qrvm.compiler import QRVMCompiler
from frontend.quar.ast_nodes import ExternalCStructDeclaration


def parse(source):
    return Parser(Lexer(source).tokenize()).parse()


SOURCE = 'extern "C" struct NativePoint { i32 x; f64 y; u32 flags; };'


class NativeStructDeclarationTests(unittest.TestCase):
    def test_layout_and_compilation(self):
        program = parse(SOURCE)
        self.assertIsInstance(program[0], ExternalCStructDeclaration)
        analyzer = SemanticAnalyzer()
        analyzer.analyze(program)
        layout = analyzer.external_c_structs['NativePoint']
        self.assertEqual(tuple(layout.fields), (('x', 'i32'), ('y', 'f64'), ('flags', 'u32')))
        self.assertIn('instructions', QRVMCompiler().compile(program))

    def test_reject_duplicate_field(self):
        with self.assertRaises(ParserError):
            parse('extern "C" struct Point { i32 x; i32 x; };')

    def test_reject_unsupported_field(self):
        with self.assertRaises(ParserError):
            parse('extern "C" struct Point { string name; };')

    def test_reject_empty_struct(self):
        with self.assertRaises(ParserError):
            parse('extern "C" struct Point { };')

    def test_reject_duplicate_struct(self):
        with self.assertRaises(SemanticError):
            SemanticAnalyzer().analyze(parse(SOURCE + SOURCE))

    def test_reject_non_c_abi(self):
        with self.assertRaises(ParserError):
            parse('extern "Rust" struct Point { i32 x; };')


if __name__ == '__main__':
    unittest.main()
