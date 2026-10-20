"""Contract tests for lexical symbol namespaces and the official coverage audit."""
import contextlib
import io
import unittest
from pathlib import Path

from frontend.quar.lexical_bytecode import LexicalBytecodeLowerer
from frontend.quar.module_loader import ModuleLoader
from frontend.quar.semantic import SemanticAnalyzer
from main import regression_project_root
from qrvm.compiler import QRVMCompiler
from qrvm.vm import QRVM
from tooling.ch1_lexical_coverage_audit import audit, report


ROOT = Path(__file__).resolve().parents[1]


class OfficialLexicalAuditTests(unittest.TestCase):
    def test_tuple_destructuring_preserves_type_pairs_and_executes(self):
        source = ROOT / "examples/0.0.3/typed/08 structured types/149 tuple destructuring.vq"
        program = SemanticAnalyzer(allow_lexical_shadowing=True).analyze(
            ModuleLoader(regression_project_root(source)).load(source)
        )
        lowered = LexicalBytecodeLowerer().lower(program)
        destructuring = next(node for node in lowered if type(node).__name__ == "DestructuringDeclaration")
        self.assertEqual([kind for kind, _ in destructuring.bindings], ["i32", "string"])
        self.assertTrue(all(name.startswith("__vq_binding_") for _, name in destructuring.bindings))
        result = io.StringIO()
        with contextlib.redirect_stdout(result):
            QRVM().run(QRVMCompiler().compile(program, lexical=True))
        self.assertEqual(result.getvalue().splitlines(), ["10", "hello"])

    def test_enum_type_namespace_and_class_metadata(self):
        for suffix, expected in [
            ("examples/0.0.3/typed/00 foundation/012 enum.vq", ["Direction.North"]),
            ("examples/0.0.4/typed/09 oop/161 class declaration.vq", ["1"]),
        ]:
            with self.subTest(path=suffix):
                path = ROOT / suffix
                program = SemanticAnalyzer(allow_lexical_shadowing=True).analyze(
                    ModuleLoader(regression_project_root(path)).load(path)
                )
                result = io.StringIO()
                with contextlib.redirect_stdout(result):
                    QRVM().run(QRVMCompiler().compile(program, lexical=True))
                self.assertEqual(result.getvalue().splitlines(), expected)

    def test_official_audit_is_complete_and_classifies_blockers(self):
        results = audit(ROOT / "examples")
        summary = report(results)
        self.assertGreaterEqual(summary["total"], 264)
        self.assertEqual(sum(summary["stages"].values()), summary["total"])
        self.assertEqual(summary["stages"].get("expected_error"), 58)
        self.assertEqual(summary["stages"].get("baseline_failed", 0), 0)
        self.assertGreater(summary["stages"].get("quarc_blocked", 0), 0)
        self.assertGreater(summary["stages"].get("c_emitted", 0), 0)


if __name__ == "__main__":
    unittest.main()
