"""Validate C/QRVM parity for while-body lexical bindings."""
import contextlib
import io
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from backend.c.codegen import CCodeGenerator
from main import build_frontend, run_qrvm


@unittest.skipUnless(shutil.which("cc"), "C compiler unavailable")
class CWhileLexicalTests(unittest.TestCase):
    def check_source(self, source, expected, *, allow_inference=False):
        program, types = build_frontend(source, lexical=True)
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            run_qrvm(program, lexical=True, allow_inference=allow_inference)
        lines = captured.getvalue().splitlines()
        start = lines.index("=== QRVM OUTPUT ===") + 1
        end = lines.index("Program executed successfully")
        self.assertEqual([line.strip() for line in lines[start:end] if line.strip()], expected)
        generated = CCodeGenerator().generate(
            program, types, lexical=True, allow_inference=allow_inference
        )
        with tempfile.TemporaryDirectory() as directory:
            c_file = Path(directory) / "loop.c"
            executable = Path(directory) / "loop"
            c_file.write_text(generated, encoding="utf-8")
            compiled = subprocess.run(
                ["cc", "-std=c11", "-Wall", "-Werror", str(c_file), "-o", str(executable)],
                capture_output=True, text=True,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            executed = subprocess.run([str(executable)], capture_output=True, text=True, timeout=5)
            self.assertEqual(executed.returncode, 0, executed.stderr)
            self.assertEqual(executed.stdout.splitlines(), expected)

    def test_typed_shadowing_inside_loop(self):
        self.check_source(
            "int counter = 0; int value = 10; "
            "while (counter < 2) { int value = 20; print(value); counter = counter + 1; } "
            "print(value);", ["20", "20", "10"]
        )

    def test_mixed_outer_assignment_inside_loop(self):
        self.check_source(
            "int counter = 0; int value = 1; "
            "while (counter < 2) { int local = 7; print(local); value = value + 1; counter = counter + 1; } "
            "print(value);", ["7", "7", "3"], allow_inference=True
        )

    def test_profile_sources_while_parity(self):
        root = Path(__file__).resolve().parents[1]
        cases = {
            "typed": ["7", "7", "5", "7", "7", "5", "9"],
            "inferred": ["7", "7", "5"],
            "mixed": ["5", "5", "1"],
        }
        for profile, expected in cases.items():
            with self.subTest(profile=profile):
                path = (root / "tests/fixtures/ch1_lexical_experimental" /
                        profile / "ch1 while lexical parity.vq")
                self.check_source(
                    path.read_text(encoding="utf-8"), expected,
                    allow_inference=profile != "typed",
                )


if __name__ == "__main__":
    unittest.main()
