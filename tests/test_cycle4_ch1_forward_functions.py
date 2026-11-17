"""Cycle 4, Chapter 1: preserve forward-call parity in every source profile."""

import contextlib
import io
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from backend.c.codegen import CCodeGenerator
from main import build_frontend
from qrvm.compiler import QRVMCompiler
from qrvm.vm import QRVM


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_OUTPUT = "6\nTrue\nFalse\n9\n"


class Cycle4Chapter1ForwardFunctionsTests(unittest.TestCase):
    def test_forward_and_mutual_calls_in_qrvm(self):
        for profile in ("typed", "inferred", "mixed"):
            with self.subTest(profile=profile):
                source = (ROOT / "examples" / "0.0.5" / profile /
                          "01 primitives" / "ch1 forward and mutual functions.vq")
                self.assertTrue(source.is_file())
                program, _ = build_frontend(source.read_text(encoding="utf-8"))
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    QRVM().run(QRVMCompiler().compile(program))
                self.assertEqual(output.getvalue(), EXPECTED_OUTPUT)

    @unittest.skipUnless(shutil.which("cc"), "C compiler is required")
    def test_forward_and_mutual_calls_in_native_c(self):
        for profile in ("typed", "inferred", "mixed"):
            with self.subTest(profile=profile):
                source = (ROOT / "examples" / "0.0.5" / profile /
                          "01 primitives" / "ch1 forward and mutual functions.vq")
                program, types = build_frontend(source.read_text(encoding="utf-8"))
                generated = CCodeGenerator().generate(program, types)
                self.assertIn("bool q_7_is_even(int32_t n);", generated)
                self.assertIn("void q_5_relay(void);", generated)
                with tempfile.TemporaryDirectory() as directory:
                    c_path = Path(directory) / "main.c"
                    executable = Path(directory) / "main"
                    c_path.write_text(generated, encoding="utf-8")
                    build = subprocess.run(
                        ["cc", "-std=c11", "-Wall", "-Werror", str(c_path),
                         "-o", str(executable)],
                        capture_output=True, text=True, timeout=10,
                    )
                    self.assertEqual(build.returncode, 0, build.stderr)
                    result = subprocess.run(
                        [str(executable)], capture_output=True, text=True, timeout=10,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout, EXPECTED_OUTPUT)

    def test_generator_does_not_keep_previous_function_signatures(self):
        generator = CCodeGenerator()
        first, first_types = build_frontend("bool enabled() { return true; } print(enabled());")
        generated = generator.generate(first, first_types)
        self.assertIn("bool q_7_enabled(void);", generated)
        second, second_types = build_frontend("print(4);")
        regenerated = generator.generate(second, second_types)
        self.assertNotIn("enabled", regenerated)
        self.assertIn('printf("%d\\n", 4)', regenerated)


if __name__ == "__main__":
    unittest.main()
