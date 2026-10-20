"""Semantic checks for explicit lexical shadowing in real Visual Quar sources."""
import unittest
from pathlib import Path

from frontend.quar.errors import SemanticError
from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from frontend.quar.semantic import SemanticAnalyzer

ROOT = Path(__file__).resolve().parents[1]


def analyze(source: str) -> None:
    program = Parser(Lexer(source).tokenize()).parse()
    SemanticAnalyzer(allow_lexical_shadowing=True).analyze(program)


class ExplicitShadowingSemanticTests(unittest.TestCase):
    def test_experimental_profiles_pass_semantic_analysis(self):
        for profile in ("typed", "inferred", "mixed"):
            with self.subTest(profile=profile):
                path = ROOT / "tests/fixtures/ch1_lexical_experimental" / profile / "ch1 lexical syntax guard.vq"
                analyze(path.read_text(encoding="utf-8"))

    def test_duplicate_in_same_nested_scope_is_rejected(self):
        with self.assertRaisesRegex(SemanticError, "already declared"):
            analyze("int value = 1; if (true) { int value = 2; int value = 3; }")

    def test_nested_shadow_type_does_not_change_outer_type(self):
        analyze('int value = 1; if (true) { string value = "local"; print(value); } value = 2;')

    def test_inferred_assignment_targets_visible_outer_variable(self):
        analyze("value = 1; if (true) { value = 2; } print(value);")


if __name__ == "__main__":
    unittest.main()
