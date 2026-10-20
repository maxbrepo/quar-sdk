"""Regression checks for comparing compiler errors across IR paths."""
import tempfile
import unittest
from pathlib import Path

from tools.ir_runtime_audit import _compile_outcome, audit_runtime_file, classify_audit_result


class CompileErrorParityTests(unittest.TestCase):
    def test_both_paths_reject_unsupported_named_argument(self):
        path = Path('examples/0.0.3/typed/05 functions/103 named arguments.vq')
        status, detail = audit_runtime_file(path)
        self.assertEqual(status, 'compile_error_equal', detail)
        self.assertIn('NamedArgument', detail)

    def test_compile_error_is_not_successfully_executed(self):
        status = classify_audit_result(Path('program.vq'), 'compile_error_equal')
        self.assertEqual(status, 'unresolved_error')

    def test_compile_error_mismatch_is_regression(self):
        status = classify_audit_result(Path('program.vq'), 'compile_error_mismatch')
        self.assertEqual(status, 'regression')


if __name__ == '__main__':
    unittest.main()
