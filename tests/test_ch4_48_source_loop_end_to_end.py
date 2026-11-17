"""Chapter 4.48: real .vq text through lexer, parser, semantics, QIR and C."""
import ctypes
from pathlib import Path
import subprocess
import tempfile
import unittest

from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from frontend.quar.semantic import SemanticAnalyzer
from frontend.quar.ast_nodes import FunctionDefinition
from frontend.quar.ir.builder import lower_statement
from frontend.quar.qir.ast_lowering import lower_ast_function
from frontend.quar.qir.legacy_bridge import lower_ir_function
from frontend.quar.qir.c_backend import emit_c_function


class SourceLoopEndToEndTests(unittest.TestCase):
    def run_source(self, source: str, expected: int) -> None:
        """Compile a real source string by both QIR routes and check native results."""
        program = Parser(Lexer(source).tokenize()).parse()
        SemanticAnalyzer().analyze(program)
        self.assertEqual(len(program), 1)
        function = program[0]
        self.assertIsInstance(function, FunctionDefinition)
        for route, qir in (
            ("direct", lower_ast_function(function)),
            ("legacy", lower_ir_function(lower_statement(function))),
        ):
            with self.subTest(route=route):
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory)
                    (path / "sample.c").write_text(emit_c_function(qir), encoding="utf-8")
                    compile_result = subprocess.run(
                        ["cc", "-std=c99", "-shared", "-fPIC", "-Werror",
                         str(path / "sample.c"), "-o", str(path / "sample.so")],
                        text=True, capture_output=True, check=False,
                    )
                    self.assertEqual(compile_result.returncode, 0, compile_result.stderr)
                    result = ctypes.CDLL(str(path / "sample.so")).sample()
                    self.assertEqual(result, expected)

    def test_while_break_continue(self):
        self.run_source("""
            i32 sample() {
                i32 i = 0;
                i32 total = 0;
                while (i < 5) {
                    i = i + 1;
                    if (i == 2) { continue; }
                    if (i == 4) { break; }
                    total = total + i;
                }
                return total;
            }
        """, 4)

    def test_for_early_return(self):
        self.run_source("""
            i32 sample() {
                i32 i = 0;
                for (i = 0; i < 8) {
                    if (i == 3) { return i + 10; }
                }
                return 0;
            }
        """, 13)

    def test_nested_loops_control(self):
        self.run_source("""
            i32 sample() {
                i32 i = 0;
                i32 j = 0;
                i32 total = 0;
                for (i = 0; i < 3) {
                    for (j = 0; j < 4) {
                        if (j == 1) { continue; }
                        if (j == 3) { break; }
                        total = total + 1;
                    }
                }
                return total;
            }
        """, 6)


if __name__ == "__main__":
    unittest.main()
