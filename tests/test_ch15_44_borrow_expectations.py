import json
import tempfile
import unittest
from pathlib import Path
from tools.borrow_expectations import classify_rows, load_expectations
from tools.borrow_regression_audit import audit_sources


class BorrowExpectationsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def source(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
        return path

    def manifest(self, cases, version=1):
        path = self.root / 'expected.json'
        path.write_text(json.dumps({'version': version, 'cases': cases}), encoding='utf-8')
        return path

    def test_positive(self):
        row, = audit_sources([self.source('good.vq', 'int x = 1;')])
        result, = classify_rows([row], self.root, {'good.vq': {'borrow': 'PASS', 'code': 'BORROW_PASS'}})
        self.assertEqual(result.classification, 'EXPECTED')

    def test_intentional_error(self):
        row, = audit_sources([self.source('bad.vq', 'int x = missing;')])
        result, = classify_rows([row], self.root, {'bad.vq': {'borrow': 'ERROR', 'code': 'BORROW_ERROR'}})
        self.assertEqual(result.classification, 'EXPECTED')

    def test_unexpected_regression(self):
        row, = audit_sources([self.source('bad.vq', 'int x = missing;')])
        result, = classify_rows([row], self.root, {'bad.vq': {'borrow': 'PASS'}})
        self.assertEqual(result.classification, 'UNEXPECTED')
        self.assertIn('expected PASS', result.reason)

    def test_unclassified(self):
        row, = audit_sources([self.source('a.vq', 'int x = 1;')])
        self.assertEqual(classify_rows([row], self.root, {})[0].classification, 'UNCLASSIFIED')

    def test_manifest_roundtrip(self):
        cases = {'nested/a.vq': {'borrow': 'UNSUPPORTED'}}
        self.assertEqual(load_expectations(self.manifest(cases)), cases)

    def test_invalid_version(self):
        with self.assertRaises(ValueError):
            load_expectations(self.manifest({}, version=2))

    def test_traversal_rejected(self):
        with self.assertRaises(ValueError):
            load_expectations(self.manifest({'../bad.vq': {'borrow': 'PASS'}}))

    def test_unknown_field_rejected(self):
        with self.assertRaises(ValueError):
            load_expectations(self.manifest({'a.vq': {'magic': 'PASS'}}))

    def test_invalid_status_rejected(self):
        with self.assertRaises(ValueError):
            load_expectations(self.manifest({'a.vq': {'borrow': 'SAFE'}}))

    def test_parity_not_run_is_not_equal(self):
        row, = audit_sources([self.source('a.vq', 'int x = 1;')])
        result, = classify_rows([row], self.root, {'a.vq': {'parity': 'runtime_equal'}})
        self.assertEqual(result.classification, 'UNEXPECTED')

    def test_parity_expected(self):
        row, = audit_sources([self.source('a.vq', 'int x = 1;')], run_parity=True)
        result, = classify_rows([row], self.root, {'a.vq': {'parity': 'runtime_equal'}})
        self.assertEqual(result.classification, 'EXPECTED')

    def test_source_outside_root(self):
        row, = audit_sources([self.source('a.vq', 'int x = 1;')])
        result, = classify_rows([row], self.root / 'other', {})
        self.assertEqual(result.classification, 'UNEXPECTED')


if __name__ == '__main__':
    unittest.main()
