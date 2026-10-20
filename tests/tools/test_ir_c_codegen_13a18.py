"""Chapter 13A.18: IR-to-C experiment, without replacing the existing backend."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from frontend.quar.module_loader import ModuleLoader
from frontend.quar.ir import lower_resolved_project
from backend.c.ir_codegen import IRCodeGenerator


class IRToCTests(unittest.TestCase):
    def test_diamond_generates_unique_definitions_and_runs(self):
        if not shutil.which("gcc"):
            self.skipTest("gcc is not available")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "shared.vq").write_text("int answer() { return 42; }\n")
            (root / "left.vq").write_text("import shared as s;\nint get() { return s.answer(); }\n")
            (root / "right.vq").write_text("import shared as t;\nint get() { return t.answer(); }\n")
            (root / "main.vq").write_text("import left as l;\nimport right as r;\n")
            loader = ModuleLoader(root)
            loader.load(root / "main.vq")
            project = lower_resolved_project(loader)
            emitter = IRCodeGenerator()
            source = emitter.generate(project)
            self.assertEqual(source.count(emitter._identifier("shared.vq::answer") + "(void) {"), 1)
            left = emitter._identifier("left.vq::get")
            right = emitter._identifier("right.vq::get")
            (root / "out.c").write_text(source + f"\nint main(void) {{ return ({left}() + {right}()) == 84 ? 0 : 1; }}\n")
            compiled = subprocess.run(["gcc", "-std=c11", "-Wall", "-Werror", str(root / "out.c"), "-o", str(root / "run")], capture_output=True, text=True)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            executed = subprocess.run([str(root / "run")], capture_output=True, text=True)
            self.assertEqual(executed.returncode, 0, executed.stderr)


if __name__ == "__main__":
    unittest.main()
