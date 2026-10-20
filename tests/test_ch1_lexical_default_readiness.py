"""Guard the default route until lexical lowering covers ordinary syntax."""
import unittest
from pathlib import Path

import main
from frontend.quar.semantic import SemanticAnalyzer
from frontend.quar.module_loader import ModuleLoader
from qrvm.compiler import QRVMCompiler


class LexicalDefaultReadinessTests(unittest.TestCase):
    def test_default_cli_remains_legacy(self):
        self.assertEqual(main.parse_lexical_options(['-f', 'demo.vq']),
                         (['-f', 'demo.vq'], False, False))

    def test_for_statement_now_has_lexical_lowering_support(self):
        root = Path(main.__file__).resolve().parent
        source = root / 'examples/0.0.3/typed/00 foundation/007 for.vq'
        self.assertTrue(source.is_file(), 'Required regression fixture is missing')
        program = ModuleLoader(main.regression_project_root(source)).load(source)
        validated = SemanticAnalyzer(allow_lexical_shadowing=True).analyze(program)
        instructions = QRVMCompiler().compile(validated, lexical=True)
        self.assertTrue(instructions)


if __name__ == '__main__':
    unittest.main()
