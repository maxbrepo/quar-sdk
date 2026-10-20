"""End-to-end opt-in lexical behavior and isolation from default compilation."""
import contextlib
import io
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from backend.c.codegen import CCodeGenerator
from main import build_frontend, run_qrvm


class LexicalPipelineContractTests(unittest.TestCase):
    def _outputs(self, source, *, allow_inference=False):
        program, types = build_frontend(source, lexical=True)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            run_qrvm(program, lexical=True, allow_inference=allow_inference)
        lines = output.getvalue().splitlines()
        start = lines.index("=== QRVM OUTPUT ===") + 1
        end = lines.index("Program executed successfully")
        qrvm = [line.strip() for line in lines[start:end] if line.strip()]
        c_output = None
        if shutil.which("cc"):
            generated = CCodeGenerator().generate(
                program, types, lexical=True, allow_inference=allow_inference
            )
            with tempfile.TemporaryDirectory() as directory:
                source_path = Path(directory) / "lexical.c"
                binary_path = Path(directory) / "lexical"
                source_path.write_text(generated, encoding="utf-8")
                compiled = subprocess.run(
                    ["cc", "-std=c11", "-Wall", "-Werror", str(source_path), "-o", str(binary_path)],
                    capture_output=True, text=True,
                )
                self.assertEqual(compiled.returncode, 0, compiled.stderr)
                executed = subprocess.run([str(binary_path)], capture_output=True, text=True)
                self.assertEqual(executed.returncode, 0, executed.stderr)
                c_output = executed.stdout.splitlines()
        return qrvm, c_output

    def test_nested_shadowing_three_levels(self):
        source = (
            "int value = 1; "
            "if (true) { int value = 2; "
            "if (true) { int value = 3; print(value); } "
            "print(value); } print(value);"
        )
        qrvm, c_output = self._outputs(source)
        self.assertEqual(qrvm, ["3", "2", "1"])
        if c_output is not None:
            self.assertEqual(c_output, qrvm)

    def test_inferred_assignment_targets_visible_outer_binding(self):
        source = (
            "value = 1; if (true) { value = 2; "
            "if (true) { value = 3; } print(value); } print(value);"
        )
        qrvm, c_output = self._outputs(source, allow_inference=True)
        self.assertEqual(qrvm, ["3", "3"])
        if c_output is not None:
            self.assertEqual(c_output, qrvm)

    def test_default_frontend_still_rejects_explicit_shadowing(self):
        source = "int value = 1; if (true) { int value = 2; }"
        with self.assertRaises(Exception):
            build_frontend(source)
        build_frontend(source, lexical=True)


if __name__ == "__main__":
    unittest.main()
