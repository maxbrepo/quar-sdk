"""Chapter 4.49: execute real .vq loop programs via the public Quarc CLI."""
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(platform.system() == "Linux" and shutil.which("gcc"),
                     "Native Linux GCC is required for CLI execution tests")
class CLISourceLoopTests(unittest.TestCase):
    def run_cli_source(self, source: str, expected_output: str) -> None:
        """Run the real CLI from a temporary .vq file and assert native output."""
        with tempfile.TemporaryDirectory() as directory:
            source_file = Path(directory) / "loop_test.vq"
            source_file.write_text(source, encoding="utf-8")
            # The target answer is consumed only when multiple compilers exist.
            result = subprocess.run(
                [sys.executable, "-u", "main.py", "-f", str(source_file)],
                input="2\n1\n1\n", text=True, capture_output=True,
                cwd=ROOT, timeout=60, env={**os.environ, "TERM": ""},
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Compilation completed successfully.", result.stdout)
            self.assertIn("Program executed successfully.", result.stdout)
            self.assertIn(f"=== PROGRAM OUTPUT ===\n{expected_output}\n", result.stdout)
            self.assertNotIn("error:", result.stdout.lower())

    def test_while_break_continue_cli(self):
        self.run_cli_source("""
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
            print(sample());
        """, "4")

    def test_for_early_return_cli(self):
        self.run_cli_source("""
            i32 sample() {
                i32 i = 0;
                for (i = 0; i < 8) {
                    if (i == 3) { return i + 10; }
                }
                return 0;
            }
            print(sample());
        """, "13")

    def test_nested_for_control_cli(self):
        self.run_cli_source("""
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
            print(sample());
        """, "6")


if __name__ == "__main__":
    unittest.main()
