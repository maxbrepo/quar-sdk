"""Chapter 13A.14 experimental module IR tests."""
import tempfile
import unittest
from pathlib import Path
from frontend.quar.module_loader import ModuleLoader
from frontend.quar.ir import lower_module_inventory


class IRInventoryTests(unittest.TestCase):
    def test_diamond_import_keeps_one_shared_module(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "shared.vq").write_text("int answer() { return 42; }\n")
            (root / "left.vq").write_text("import shared as s;\nint get() { return s.answer(); }\n")
            (root / "right.vq").write_text("import shared as t;\nint get() { return t.answer(); }\n")
            (root / "main.vq").write_text("import left as l;\nimport right as r;\nprint(l.get() + r.get());\n")
            loader = ModuleLoader(root)
            loader.load(root / "main.vq")
            project = lower_module_inventory(loader)
            names = [module.module_id for module in project.modules]
            self.assertEqual(names.count("shared.vq"), 1)
            self.assertEqual(len(names), 4)
            self.assertEqual(names[-1], "main.vq")
            shared = next(module for module in project.modules if module.module_id == "shared.vq")
            self.assertEqual(shared.functions[0].symbol, "shared.vq::answer")


if __name__ == "__main__":
    unittest.main()
