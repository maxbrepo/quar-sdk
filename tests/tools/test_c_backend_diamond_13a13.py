"""Chapter 13A.13: end-to-end single-C shared-module regression."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from frontend.quar.module_loader import ModuleLoader
from frontend.quar.semantic import SemanticAnalyzer
from backend.c.codegen import CCodeGenerator


class DiamondCBackendTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("gcc"), "GCC is required")
    def test_shared_dependency_compiles_and_runs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "shared.vq").write_text("int answer() { return 42; }\n")
            (root / "left.vq").write_text("import shared as s;\nint get() { return s.answer(); }\n")
            (root / "right.vq").write_text("import shared as t;\nint get() { return t.answer(); }\n")
            (root / "main.vq").write_text("import left as l;\nimport right as r;\nprint(l.get() + r.get());\n")
            loader = ModuleLoader(root)
            loader.load(root / "main.vq")
            program = SemanticAnalyzer().analyze(loader.canonical_program())
            generated = CCodeGenerator().generate(program)
            source = root / "generated.c"
            source.write_text(generated)
            executable = root / "program"
            build = subprocess.run(["gcc", "-std=c11", "-Wall", "-Werror", str(source), "-o", str(executable)], capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            execution = subprocess.run([str(executable)], capture_output=True, text=True)
            self.assertEqual(execution.returncode, 0, execution.stderr)
            self.assertEqual(execution.stdout.strip(), "84")


if __name__ == "__main__":
    unittest.main()
