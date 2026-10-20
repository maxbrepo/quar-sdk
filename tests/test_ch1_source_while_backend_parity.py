"""Verify lexical shadowing parity using real Visual Quar source files."""
import contextlib
import io
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from backend.c.codegen import CCodeGenerator
from main import build_frontend, run_qrvm


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "ch1_lexical_experimental"
EXPECTED = {
    "typed": ["7", "7", "5", "7", "7", "5", "9"],
    "inferred": ["7", "7", "5"],
    "mixed": ["5", "5", "1"],
}


class SourceWhileBackendParityTests(unittest.TestCase):
    def test_real_source_matches_qrvm_and_c(self):
        for profile, expected in EXPECTED.items():
            with self.subTest(profile=profile):
                source_file = FIXTURES / profile / "ch1 while lexical parity.vq"
                self.assertTrue(source_file.is_file())
                program, types = build_frontend(
                    source_file.read_text(encoding="utf-8"), lexical=True
                )
                inference = profile != "typed"
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    run_qrvm(program, lexical=True, allow_inference=inference)
                lines = output.getvalue().splitlines()
                start = lines.index("=== QRVM OUTPUT ===") + 1
                end = lines.index("Program executed successfully")
                vm_lines = [line.strip() for line in lines[start:end] if line.strip()]
                self.assertEqual(vm_lines, expected)

                if not shutil.which("cc"):
                    continue
                c_source = CCodeGenerator().generate(
                    program, types, lexical=True, allow_inference=inference
                )
                with tempfile.TemporaryDirectory() as directory:
                    source = Path(directory) / "program.c"
                    binary = Path(directory) / "program"
                    source.write_text(c_source, encoding="utf-8")
                    build = subprocess.run(
                        ["cc", "-std=c11", "-Wall", "-Werror", str(source), "-o", str(binary)],
                        capture_output=True, text=True, timeout=20,
                    )
                    self.assertEqual(build.returncode, 0, build.stderr)
                    result = subprocess.run(
                        [str(binary)], capture_output=True, text=True, timeout=10,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout.splitlines(), expected)


if __name__ == "__main__":
    unittest.main()
