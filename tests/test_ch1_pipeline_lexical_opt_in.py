"""Exercise the opt-in lexical path through the ordinary frontend entry point."""
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
EXPECTED = {"typed": ["3", "1"], "inferred": ["3", "2"], "mixed": ["3", "4", "1"]}


class LexicalPipelineOptInTests(unittest.TestCase):
    def test_all_profiles_via_frontend_and_qrvm(self):
        for profile, expected in EXPECTED.items():
            with self.subTest(profile=profile):
                path = ROOT / "tests/fixtures/ch1_lexical_experimental" / profile / "ch1 lexical syntax guard.vq"
                program, types = build_frontend(path.read_text(encoding="utf-8"), lexical=True)
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    run_qrvm(program, lexical=True, allow_inference=profile != "typed")
                lines = output.getvalue().splitlines()
                start = lines.index("=== QRVM OUTPUT ===") + 1
                end = lines.index("Program executed successfully")
                observed = [line.strip() for line in lines[start:end] if line.strip()]
                self.assertEqual(observed, expected)
                if shutil.which("cc"):
                    source = CCodeGenerator().generate(program, types, lexical=True, allow_inference=profile != "typed")
                    with tempfile.TemporaryDirectory() as directory:
                        c_file = Path(directory) / "sample.c"
                        binary = Path(directory) / "sample"
                        c_file.write_text(source, encoding="utf-8")
                        compiled = subprocess.run(["cc", "-std=c11", "-Wall", "-Werror", str(c_file), "-o", str(binary)], capture_output=True, text=True)
                        self.assertEqual(compiled.returncode, 0, compiled.stderr)
                        result = subprocess.run([str(binary)], capture_output=True, text=True)
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertEqual(result.stdout.splitlines(), expected)


if __name__ == "__main__":
    unittest.main()
