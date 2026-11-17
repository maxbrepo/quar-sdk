"""Validate the Chapter 5 user examples through the real frontend."""
from pathlib import Path
import unittest
from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from frontend.quar.semantic import SemanticAnalyzer

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "0.0.5"

class Chapter5UserExamplesTests(unittest.TestCase):
    def test_example_sources(self):
        paths = sorted(EXAMPLES.glob("*/05 types/*.vq"))
        self.assertGreaterEqual(len(paths), 9, "Expected at least three examples for each type mode")
        for mode in ("typed", "inferred", "mixed"):
            self.assertGreaterEqual(len(list((EXAMPLES / mode / "05 types").glob("*.vq"))), 3)
        for path in paths:
            with self.subTest(example=str(path.relative_to(EXAMPLES))):
                source = path.read_text(encoding="utf-8")
                program = Parser(Lexer(source).tokenize()).parse()
                SemanticAnalyzer().analyze(program)

if __name__ == "__main__":
    unittest.main()
