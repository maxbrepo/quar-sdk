import tempfile
import unittest
from pathlib import Path
from tools.borrow_baseline import candidate_baseline, approve_baseline
from tools.borrow_expectations import classify_rows
from tools.borrow_regression_audit import audit_sources


class BorrowBaselineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def put(self, name, text):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')
        return p

    def test_unapproved_candidate(self):
        self.put('good.vq', 'int x = 1;')
        candidate = candidate_baseline(self.root)
        self.assertFalse(candidate['cases']['good.vq']['reviewed'])

    def test_approved_good(self):
        path = self.put('good.vq', 'int x = 1;')
        baseline = approve_baseline(candidate_baseline(self.root), self.root, ['good.vq'])
        self.assertEqual(baseline['cases']['good.vq']['borrow'], 'PASS')
        self.assertEqual(classify_rows(audit_sources([path]), self.root, baseline['cases'])[0].classification, 'EXPECTED')

    def test_negative_requires_review(self):
        self.put('bad.vq', 'int x = missing;')
        candidate = candidate_baseline(self.root)
        self.assertEqual(candidate['cases']['bad.vq']['observed']['borrow'], 'ERROR')
        with self.assertRaises(ValueError):
            approve_baseline(candidate, self.root, [])
        self.assertEqual(approve_baseline(candidate, self.root, ['bad.vq'])['cases']['bad.vq']['borrow'], 'ERROR')

    def test_changed_file_rejected(self):
        self.put('a.vq', 'int x = 1;')
        candidate = candidate_baseline(self.root)
        self.put('a.vq', 'int x = 2;')
        with self.assertRaisesRegex(ValueError, 'changed'):
            approve_baseline(candidate, self.root, ['a.vq'])

    def test_unknown_review_rejected(self):
        self.put('a.vq', 'int x = 1;')
        with self.assertRaises(ValueError):
            approve_baseline(candidate_baseline(self.root), self.root, ['unknown.vq'])

    def test_input_excluded(self):
        self.put('input/interactive.vq', 'int x = 1;')
        self.put('ok.vq', 'int x = 1;')
        self.assertEqual(set(candidate_baseline(self.root)['cases']), {'ok.vq'})

    def test_file_limit(self):
        self.put('a.vq', 'int x = 1;')
        self.put('b.vq', 'int x = 2;')
        with self.assertRaises(ValueError):
            candidate_baseline(self.root, max_files=1)

    def test_root_mismatch(self):
        self.put('a.vq', 'int x = 1;')
        with self.assertRaises(ValueError):
            approve_baseline(candidate_baseline(self.root), self.root / 'other', ['a.vq'])

    def test_internal_failure_rejected(self):
        self.put('a.vq', 'int x = 1;')
        candidate = candidate_baseline(self.root)
        candidate['cases']['a.vq']['observed'] = {'borrow': 'AUDIT_ERROR', 'code': 'BORROW_INTERNAL_ERROR'}
        with self.assertRaisesRegex(ValueError, 'internal'):
            approve_baseline(candidate, self.root, ['a.vq'])

    def test_no_files(self):
        self.assertEqual(candidate_baseline(self.root)['cases'], {})


if __name__ == '__main__':
    unittest.main()
