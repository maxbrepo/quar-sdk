"""End-to-end IR entrypoint parity for unified and split C layouts."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from frontend.quar.ir import lower_program_project
from frontend.quar.module_loader import ModuleLoader
from tooling.ir_build import CLayout, emit_c, compile_objects, link_executable

class IREntryTests(unittest.TestCase):
    def test_entrypoint_returns_same_exit_code_in_both_layouts(self):
        if not shutil.which("gcc"):
            self.skipTest("gcc unavailable")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "shared.vq").write_text("int answer() { return 42; }\n")
            (root / "left.vq").write_text("import shared as s;\nint get() { return s.answer(); }\n")
            (root / "right.vq").write_text("import shared as t;\nint get() { return t.answer(); }\n")
            entry = root / "main.vq"
            entry.write_text("import left as l;\nimport right as r;\nreturn l.get() + r.get();\n")
            loader = ModuleLoader(root)
            loader.load(entry)
            project = lower_program_project(loader, entry)
            for layout in CLayout:
                with self.subTest(layout=layout):
                    output = root / layout.value
                    artifacts = emit_c(project, output, layout)
                    objects = compile_objects(artifacts, output)
                    executable = link_executable(objects, output / "app")
                    result = subprocess.run([str(executable)], check=False)
                    self.assertEqual(result.returncode, 84)

if __name__ == "__main__":
    unittest.main()
