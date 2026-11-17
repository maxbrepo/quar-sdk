"""Marathon 2, chapter 5: frontend-only integer and mixed inference regressions.

No QIR, C transpiler, native compiler or external toolchain is involved.
"""
import unittest

from frontend.quar.errors import SemanticError
from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from frontend.quar.semantic import SemanticAnalyzer


class SemanticTypeMatrixTests(unittest.TestCase):
    def check_source(self, source: str, expected_types: dict[str, str] | None = None) -> None:
        """Analyze source and optionally assert the final resolved variable types."""
        program = Parser(Lexer(source).tokenize()).parse()
        analyzer = SemanticAnalyzer()
        analyzer.analyze(program)
        if expected_types:
            for name, expected in expected_types.items():
                self.assertEqual(analyzer.variables[name], expected)

    def test_signed_integer_boundaries(self):
        for name, bits in (("i8", 8), ("i16", 16), ("i32", 32), ('i64', 64), ('i128', 128)):
            minimum, maximum = -(1 << (bits - 1)), (1 << (bits - 1)) - 1
            for value in (minimum, maximum):
                with self.subTest(type=name, value=value):
                    self.check_source(f"{name} x = {value};")
            for value in (minimum - 1, maximum + 1):
                with self.subTest(type=name, invalid=value):
                    with self.assertRaises(SemanticError):
                        self.check_source(f"{name} x = {value};")

    def test_unsigned_integer_boundaries(self):
        for name, bits in (("u8", 8), ("u16", 16), ("u32", 32), ('u64', 64), ('u128', 128)):
            for value in (0, (1 << bits) - 1):
                with self.subTest(type=name, value=value):
                    self.check_source(f"{name} x = {value};")
            for value in (-1, 1 << bits):
                with self.subTest(type=name, invalid=value):
                    with self.assertRaises(SemanticError):
                        self.check_source(f"{name} x = {value};")

    def test_safe_widening(self):
        self.check_source("i8 small = 7; i16 wide = small;")
        self.check_source("u8 small = 7; i16 wide = small;")

    def test_unsafe_narrowing_rejected(self):
        with self.assertRaises(SemanticError):
            self.check_source("i16 wide = 7; i8 narrow = wide;")

    def test_signed_to_unsigned_rejected(self):
        with self.assertRaises(SemanticError):
            self.check_source("i8 signed_value = 7; u8 unsigned_value = signed_value;")

    def test_unsigned_to_signed_same_width_rejected(self):
        with self.assertRaises(SemanticError):
            self.check_source("u8 unsigned_value = 7; i8 signed_value = unsigned_value;")

    def test_inferred_first_assignment(self):
        self.check_source("number = 7;", {"number": "int"})

    def test_mixed_inferred_and_typed(self):
        self.check_source("i16 typed_value = 7; inferred_value = typed_value; i32 wide = inferred_value;",
                          {"inferred_value": "i16", "wide": "i32"})

    def test_inferred_reassignment_keeps_type(self):
        self.check_source("value = 7; value = 8;", {"value": "int"})

    def test_inferred_reassignment_rejects_incompatible_type(self):
        with self.assertRaises(SemanticError):
            self.check_source('value = 7; value = "text";')


if __name__ == "__main__":
    unittest.main()
