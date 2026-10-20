"""End-to-end Chapter 13 module examples and batch discovery."""

import unittest
from pathlib import Path

from main import collect_batch_sources, execute_regression_source


ROOT = Path(__file__).resolve().parents[1]
MODULES = ROOT / "examples" / "0.0.4" / "typed" / "13 modules"


class ModuleRegressionParityTests(unittest.TestCase):
    def test_module_projects_execute_from_entrypoint(self):
        expected = {234: "42", 235: "42", 236: "49", 237: "42", 238: "42"}
        for folder in sorted(MODULES.iterdir()):
            if not folder.is_dir():
                continue
            number = int(folder.name.split()[0])
            with self.subTest(project=number):
                self.assertEqual(execute_regression_source(folder / "main.vq"),
                                 ("PASS", expected[number]))

    def test_batch_runs_only_module_entrypoints(self):
        sources = collect_batch_sources(MODULES)
        self.assertEqual(len(sources), 5)
        self.assertTrue(all(path.name == "main.vq" for path in sources))


if __name__ == "__main__":
    unittest.main()
