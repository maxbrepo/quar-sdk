"""Regression coverage for the original 0.0.1 example and non-interactive CLI."""
import os
import shutil
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from main import ask_program_execution, clear_screen


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/0.0.1/000 example.vq"


class FirstExampleCLITests(unittest.TestCase):
    def test_original_example_interpreted(self):
        result = subprocess.run(
            [sys.executable, "-u", "main.py", "-f", str(EXAMPLE)],
            input="1\n", text=True, capture_output=True, cwd=ROOT,
            timeout=30, env={**os.environ, "TERM": ""},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Program executed successfully", result.stdout)
        self.assertIn("20", result.stdout)
        self.assertNotIn("TERM environment variable not set", result.stderr)

    def test_original_example_compiled_and_executed(self):
        """Compile and execute the first example through the actual CLI path."""
        # A cross-compiler adds a target-selection prompt before the run prompt.
        target_answer = "1\n" if shutil.which("x86_64-w64-mingw32-gcc") else ""
        result = subprocess.run(
            [sys.executable, "-u", "main.py", "-f", str(EXAMPLE)],
            input="2\n" + target_answer + "1\n", text=True, capture_output=True, cwd=ROOT,
            timeout=45, env={**os.environ, "TERM": ""},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Compilation completed successfully", result.stdout)
        self.assertIn("Program executed successfully", result.stdout)
        self.assertIn("=== PROGRAM OUTPUT ===\n20", result.stdout)
        self.assertNotIn("TERM environment variable not set", result.stderr)

    def test_missing_execution_answer_skips_run(self):
        with patch("builtins.input", side_effect=EOFError):
            self.assertFalse(ask_program_execution("linux-x64", "linux"))

    def test_clear_screen_without_terminal(self):
        with patch("sys.stdout.isatty", return_value=False), patch("subprocess.run") as run:
            clear_screen()
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
