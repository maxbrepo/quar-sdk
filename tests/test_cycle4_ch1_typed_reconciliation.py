"""Cycle 4, Chapter 1: preserve source-profile and backend parity."""

import contextlib
import io
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from backend.c.codegen import CCodeGenerator
from frontend.quar.ast_nodes import Assignment, FunctionDefinition, Integer
from main import build_frontend
from qrvm.compiler import QRVMCompiler
from qrvm.vm import QRVM


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
NEW_VERSION = "0.0.5"
HISTORICAL_VERSION = "0.0.4"


def example_path(profile: str, filename: str) -> Path:
    """Find each parity fixture in the version where it was introduced."""
    if profile == "typed" and filename in {
        "ch1 function and local values.vq", "ch1 nested scope baseline.vq"
    }:
        version = NEW_VERSION
    else:
        version = HISTORICAL_VERSION
    return EXAMPLES / version / profile / "01 primitives" / filename
EXPECTED_OUTPUT = {
    "ch1 constants and assignments.vq": "5\n",
    "ch1 function and local values.vq": "30\n",
    "ch1 function scope isolation.vq": "11\n22\n",
    "ch1 nested scope baseline.vq": "15\n10\n",
    "ch1 nested scope isolation.vq": "15\n10\n",
    "ch1 outer assignment across scopes.vq": "20\n30\n",
    "ch1 sibling branch scopes.vq": "1\n10\n",
}


class Cycle4Chapter1ProfileParityTests(unittest.TestCase):
    def test_all_three_profiles_have_matching_qrvm_results(self):
        for filename, expected in EXPECTED_OUTPUT.items():
            for profile in ("typed", "inferred", "mixed"):
                with self.subTest(example=filename, profile=profile):
                    path = example_path(profile, filename)
                    self.assertTrue(path.is_file(), str(path))
                    program, _ = build_frontend(path.read_text(encoding="utf-8"))
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        QRVM().run(QRVMCompiler().compile(program))
                    self.assertEqual(output.getvalue(), expected)

    @unittest.skipUnless(shutil.which("cc"), "C compiler is required")
    def test_all_three_profiles_have_matching_c_results(self):
        for filename, expected in EXPECTED_OUTPUT.items():
            for profile in ("typed", "inferred", "mixed"):
                with self.subTest(example=filename, profile=profile):
                    path = example_path(profile, filename)
                    program, types = build_frontend(path.read_text(encoding="utf-8"))
                    c_source = CCodeGenerator().generate(program, types)
                    with tempfile.TemporaryDirectory() as directory:
                        source = Path(directory) / "main.c"
                        executable = Path(directory) / "main"
                        source.write_text(c_source, encoding="utf-8")
                        build = subprocess.run(
                            ["cc", "-std=c11", "-Wall", "-Werror", str(source),
                             "-o", str(executable)],
                            capture_output=True, text=True, timeout=10,
                        )
                        self.assertEqual(build.returncode, 0, build.stderr)
                        result = subprocess.run(
                            [str(executable)], capture_output=True, text=True, timeout=10,
                        )
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertEqual(result.stdout, expected)

    def test_inferred_function_local_does_not_relax_global_validation(self):
        # Function-local first assignments are legal after frontend validation.
        # An unknown top-level assignment must remain rejected by this backend.
        generator = CCodeGenerator()
        program = [FunctionDefinition("void", "noop", [], []),
                   Assignment("unknown", Integer(1))]
        with self.assertRaisesRegex(ValueError, "Unknown assignment target"):
            generator.generate(program)

    def test_backend_function_context_is_restored_after_generation(self):
        generator = CCodeGenerator()
        source = example_path("inferred", "ch1 function and local values.vq").read_text(encoding="utf-8")
        program, types = build_frontend(source)
        generated = generator.generate(program, types)
        self.assertIn("int32_t result = (left + right);", generated)
        with self.assertRaisesRegex(ValueError, "Unknown assignment target"):
            generator.generate([Assignment("unknown", Integer(1))])


if __name__ == "__main__":
    unittest.main()
