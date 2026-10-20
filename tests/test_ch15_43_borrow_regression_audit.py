import tempfile
import unittest
from pathlib import Path
from tools.borrow_regression_audit import audit_sources, discover_sources


class BorrowRegressionAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def write(self, name, source):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding='utf-8')
        return path

    def test_valid(self):
        row, = audit_sources([self.write('valid.vq', 'int x = 1;')])
        self.assertEqual((row.borrow_status, row.borrow_code, row.parity_status), ('PASS', 'BORROW_PASS', 'NOT_RUN'))

    def test_invalid(self):
        row, = audit_sources([self.write('invalid.vq', 'int x = missing;')])
        self.assertEqual(row.borrow_status, 'ERROR')

    def test_unsupported(self):
        row, = audit_sources([self.write('print.vq', 'print(1);')])
        self.assertEqual(row.borrow_status, 'UNSUPPORTED')

    def test_read_failure(self):
        row, = audit_sources([self.root / 'absent.vq'])
        self.assertEqual(row.borrow_code, 'SOURCE_READ_ERROR')

    def test_limit(self):
        a = self.write('a.vq', 'int a = 1;')
        b = self.write('b.vq', 'int b = 1;')
        with self.assertRaises(ValueError):
            audit_sources([a, b], max_files=1)

    def test_duplicate_deduplicated(self):
        path = self.write('a.vq', 'int a = 1;')
        self.assertEqual(len(audit_sources([path, path])), 1)

    def test_input_excluded(self):
        self.write('input/interactive.vq', 'int x = 1;')
        self.write('safe.vq', 'int x = 1;')
        self.assertEqual([p.name for p in discover_sources(self.root)], ['safe.vq'])

    def test_parity_safe_program(self):
        row, = audit_sources([self.write('simple.vq', 'int x = 1;')], run_parity=True)
        self.assertEqual(row.parity_status, 'runtime_equal', row.detail)

    def test_parity_does_not_override_borrow(self):
        row, = audit_sources([self.write('simple.vq', 'int x = 1;')], run_parity=True)
        self.assertEqual(row.borrow_status, 'PASS')

    def test_negative_max_files(self):
        with self.assertRaises(ValueError):
            audit_sources([], max_files=0)


if __name__ == '__main__':
    unittest.main()
