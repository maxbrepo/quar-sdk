"""Chapter 13A.17: canonical IR symbols, validation and text inspection."""
import tempfile
import unittest
from pathlib import Path
from frontend.quar.module_loader import ModuleLoader
from frontend.quar.ir import (lower_resolved_project, validate_project,
                              IRValidationError, format_project, IRCall, IRReturn)


class IR13A17Tests(unittest.TestCase):
    def build_diamond(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        (root / 'shared.vq').write_text('int answer() { return 42; }\n')
        (root / 'left.vq').write_text('import shared as s;\nint get() { return s.answer(); }\n')
        (root / 'right.vq').write_text('import shared as t;\nint get() { return t.answer(); }\n')
        (root / 'main.vq').write_text('import left as l;\nimport right as r;\n')
        loader = ModuleLoader(root)
        loader.load(root / 'main.vq')
        return temp, lower_resolved_project(loader)

    def test_aliases_resolve_to_same_symbol(self):
        temp, project = self.build_diamond()
        try:
            calls = [module.functions[0].body[0].value.symbol for module in project.modules
                     if module.module_id in ('left.vq', 'right.vq')]
            self.assertEqual(calls, ['shared.vq::answer', 'shared.vq::answer'])
            validate_project(project)
        finally:
            temp.cleanup()

    def test_inspection_is_deterministic(self):
        temp, project = self.build_diamond()
        try:
            output = format_project(project)
            self.assertEqual(output.count('module shared.vq\n'), 1)
            self.assertIn('function shared.vq::answer()', output)
            self.assertEqual(output, format_project(project))
        finally:
            temp.cleanup()

    def test_missing_symbol_is_rejected(self):
        from dataclasses import replace
        temp, project = self.build_diamond()
        try:
            module = project.modules[1]
            function = module.functions[0]
            broken = replace(function, body=(IRReturn(IRCall('missing.vq::nope', ())),))
            bad_module = replace(module, functions=(broken,))
            bad_project = replace(project, modules=(project.modules[0], bad_module, *project.modules[2:]))
            with self.assertRaises(IRValidationError):
                validate_project(bad_project)
        finally:
            temp.cleanup()
