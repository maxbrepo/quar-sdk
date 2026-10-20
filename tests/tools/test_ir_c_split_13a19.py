"""Verify split C compilation and linking with a shared diamond dependency."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from backend.c.ir_codegen import IRCodeGenerator
from frontend.quar.ir import lower_resolved_project
from frontend.quar.module_loader import ModuleLoader


class SplitC13A19Tests(unittest.TestCase):
    def test_split_c_compiles_each_module_and_links(self):
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
            generator = IRCodeGenerator()
            outputs = generator.generate_split(project)
            self.assertEqual(len(outputs), len(project.modules) + 1)
            for filename, contents in outputs.items():
                (root / filename).write_text(contents)
            objects = []
            for filename in outputs:
                if not filename.endswith(".c"):
                    continue
                obj = root / (filename + ".o")
                result = subprocess.run(["gcc", "-std=c11", "-Wall", "-Werror",
                                         "-c", str(root / filename), "-o", str(obj)],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                objects.append(str(obj))
            left = generator._identifier("left.vq::get")
            right = generator._identifier("right.vq::get")
            (root / "entry.c").write_text(
                '#include "quar_generated.h"\n'
                f'int main(void) {{ return ({left}() + {right}()) == 84 ? 0 : 1; }}\n')
            result = subprocess.run(["gcc", "-std=c11", "-Wall", "-Werror",
                                     str(root / "entry.c"), *objects, "-o", str(root / "run")],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([str(root / "run")], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
