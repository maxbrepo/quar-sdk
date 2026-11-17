"""Chapter 5: user-facing examples across typed, inferred, and mixed modes."""
import unittest
from pathlib import Path
from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from frontend.quar.semantic import SemanticAnalyzer

ROOT = Path(__file__).resolve().parents[1] / "examples" / "0.0.5"
NEW_EXAMPLES = {
    "typed": ("ch5 integer aliases.vq", "ch5 signed widening chain.vq"),
    "inferred": ("ch5 inferred arithmetic chain.vq", "ch5 inferred function argument.vq"),
    "mixed": ("ch5 mixed function pipeline.vq", "ch5 mixed inferred arithmetic.vq"),
}

class Chapter5InferenceExamples(unittest.TestCase):
    def test_source_examples(self):
        for mode, names in NEW_EXAMPLES.items():
            for name in names:
                with self.subTest(mode=mode, name=name):
                    path = ROOT / mode / "05 types" / name
                    self.assertTrue(path.is_file())
                    source = path.read_text(encoding="utf-8")
                    program = Parser(Lexer(source).tokenize()).parse()
                    SemanticAnalyzer().analyze(program)

if __name__ == "__main__":
    unittest.main()
