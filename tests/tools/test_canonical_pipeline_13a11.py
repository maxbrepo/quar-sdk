"""Chapter 13A.11: canonical module pipeline integration tests."""
import tempfile
import unittest
from pathlib import Path
from frontend.quar.module_loader import ModuleLoader
from frontend.quar.semantic import SemanticAnalyzer
from frontend.quar.ast_nodes import FunctionDefinition
from qrvm.compiler import QRVMCompiler
from qrvm.vm import QRVM

class CanonicalPipelineTests(unittest.TestCase):
    def test_existing_valid_module_examples_in_vm(self):
        source_dir = Path(__file__).resolve().parents[2] / "examples/0.0.3/typed/XX modules"
        for number in range(41, 46):
            with self.subTest(number=number):
                source = next(source_dir.glob(f"{number:03d} *.vq"))
                loader = ModuleLoader(source_dir / "fixtures")
                loader.load(source)
                program = SemanticAnalyzer().analyze(loader.canonical_program())
                QRVM().run(QRVMCompiler().compile(program))

    def test_diamond_dependency_has_one_definition_and_executes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "shared.vq").write_text("int answer() { return 42; }\n")
            (root / "left.vq").write_text("import shared as s;\nint get() { return s.answer(); }\n")
            (root / "right.vq").write_text("import shared as t;\nint get() { return t.answer(); }\n")
            (root / "main.vq").write_text("import left as l;\nimport right as r;\nprint(l.get() + r.get());\n")
            loader = ModuleLoader(root)
            loader.load(root / "main.vq")
            program = loader.canonical_program()
            names = [node.name for node in program if isinstance(node, FunctionDefinition)]
            self.assertEqual(names.count("shared.answer"), 1)
            SemanticAnalyzer().analyze(program)
            QRVM().run(QRVMCompiler().compile(program))

if __name__ == "__main__":
    unittest.main()
