"""Regression tests for project-aware IR/QRVM parity auditing."""
import tempfile
import unittest
from pathlib import Path

from tools.ir_runtime_audit import audit_runtime_file


class IRImportAuditTests(unittest.TestCase):
    def test_project_import_executes_through_both_pipelines(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'helper.vq').write_text('int answer() { return 42; }', encoding='utf-8')
            entry = root / 'main.vq'
            entry.write_text('import helper; int result = helper.answer();', encoding='utf-8')
            status, detail = audit_runtime_file(entry)
            self.assertEqual(status, 'runtime_equal', detail)

    def test_missing_module_is_classified_as_module_error(self):
        with tempfile.TemporaryDirectory() as directory:
            entry = Path(directory) / 'main.vq'
            entry.write_text('import absent; print(1);', encoding='utf-8')
            status, detail = audit_runtime_file(entry)
            self.assertEqual(status, 'module_error')
            self.assertIn('Module not found', detail)


if __name__ == '__main__':
    unittest.main()
