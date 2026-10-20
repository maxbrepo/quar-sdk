"""Compare native C output with QRVM for stable, real Visual Quar sources."""
import contextlib
import io
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from backend.c.codegen import CCodeGenerator
from frontend.quar.module_loader import ModuleLoader
from frontend.quar.semantic import SemanticAnalyzer
from main import build_frontend, regression_project_root
from qrvm.compiler import QRVMCompiler
from qrvm.vm import QRVM


ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("cc"), "C compiler is required")
class OfficialLexicalParityTests(unittest.TestCase):
    def assert_program_parity(self, program, types, expected):
        vm_output = io.StringIO()
        with contextlib.redirect_stdout(vm_output):
            QRVM().run(QRVMCompiler().compile(program, lexical=True))
        self.assertEqual(vm_output.getvalue().splitlines(), expected)
        generated = CCodeGenerator().generate(program, types, lexical=True)
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "program.c"
            executable = Path(directory) / "program"
            source.write_text(generated, encoding="utf-8")
            build = subprocess.run(
                ["cc", "-std=c11", "-Wall", "-Werror", str(source), "-o", str(executable)],
                capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(build.returncode, 0, build.stderr)
            result = subprocess.run(
                [str(executable)], capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.splitlines(), expected)

    def test_official_boolean_logic(self):
        source = ROOT / "examples/0.0.3/typed/00 foundation/004 logic.vq"
        semantic = SemanticAnalyzer(allow_lexical_shadowing=True)
        program = semantic.analyze(ModuleLoader(regression_project_root(source)).load(source))
        self.assert_program_parity(program, semantic.variables,
                                   ["True", "False", "True", "True", "True", "True"])

    def test_official_void_function(self):
        source = ROOT / "examples/0.0.3/typed/00 foundation/023 void functions.vq"
        semantic = SemanticAnalyzer(allow_lexical_shadowing=True)
        program = semantic.analyze(ModuleLoader(regression_project_root(source)).load(source))
        self.assert_program_parity(program, semantic.variables, ["23"])

    def test_typed_implicit_for_counter_remains_visible(self):
        source = "for (i = 0; i < 3) { print(i); } print(i);"
        program, types = build_frontend(source, lexical=True)
        self.assert_program_parity(program, types, ["0", "1", "2", "3"])


if __name__ == "__main__":
    unittest.main()
