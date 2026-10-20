"""Exercise the shared single/split C artifact and object build API."""
import shutil
import tempfile
import unittest
from pathlib import Path

from frontend.quar.ir import lower_resolved_project
from frontend.quar.module_loader import ModuleLoader
from tooling.ir_build import CLayout, emit_c, compile_objects


class IRBuild13A20Tests(unittest.TestCase):
    def test_single_and_split_emit_and_compile(self):
        if not shutil.which("gcc"):
            self.skipTest("gcc unavailable")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "shared.vq").write_text("int answer() { return 42; }\n")
            (root / "left.vq").write_text("import shared as s;\nint get() { return s.answer(); }\n")
            (root / "right.vq").write_text("import shared as t;\nint get() { return t.answer(); }\n")
            (root / "main.vq").write_text("import left as l;\nimport right as r;\n")
            loader = ModuleLoader(root)
            loader.load(root / "main.vq")
            project = lower_resolved_project(loader)
            for layout in CLayout:
                with self.subTest(layout=layout):
                    directory = root / layout.value
                    artifacts = emit_c(project, directory, layout)
                    self.assertEqual(len(artifacts.sources),
                                     1 if layout is CLayout.SINGLE else len(project.modules))
                    self.assertEqual(len(artifacts.headers),
                                     0 if layout is CLayout.SINGLE else 1)
                    objects = compile_objects(artifacts, directory)
                    self.assertEqual(len(objects), len(artifacts.sources))
                    self.assertTrue(all(path.is_file() for path in objects))

    def test_unknown_layout_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                emit_c(None, Path(temp), "mixed")

if __name__ == "__main__":
    unittest.main()
