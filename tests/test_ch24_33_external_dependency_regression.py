"""Keep native-library examples visible without treating them as standalone programs."""
from pathlib import Path
import tempfile
import unittest

from main import execute_regression_source, regression_native_dependency
from tooling.ch1_lexical_coverage_audit import audit

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/0.0.5/typed/24_interoperability/24_14_sdl_visible_window.vq"


class ExternalDependencyRegressionTests(unittest.TestCase):
    def test_sdl_example_is_explicitly_classified(self):
        self.assertEqual(regression_native_dependency(EXAMPLE), "SDL2")
        status, description = execute_regression_source(EXAMPLE)
        self.assertEqual(status, "EXTERNAL DEPENDENCY")
        self.assertIn("SDL2", description)

    def test_unmarked_source_is_not_silently_exempt(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "plain.vq"
            source.write_text('extern "C" i32 missing_native();\nprint(missing_native());\n', encoding="utf-8")
            self.assertIsNone(regression_native_dependency(source))
            status, _ = execute_regression_source(source)
            self.assertEqual(status, "FAIL")

    def test_audit_reports_explicit_external_dependency(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "0.0.5" / "typed" / "24_interoperability" / EXAMPLE.name
            source.parent.mkdir(parents=True)
            source.write_text(EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
            source.with_name(source.name + ".native.json").write_text(
                EXAMPLE.with_name(EXAMPLE.name + ".native.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            results = audit(root)
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].stage, "external_dependency")
            self.assertEqual(results[0].reason, "SDL2")


if __name__ == "__main__":
    unittest.main()
