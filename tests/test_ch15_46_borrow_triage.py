import tempfile
import unittest
from pathlib import Path
from tools.borrow_baseline import candidate_baseline
from tools.borrow_triage import classify_candidate, triage_summary


class TriageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def put(self, name, text):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')
        return p

    def triage(self):
        return classify_candidate(candidate_baseline(self.root), self.root)

    def test_pass_not_approved(self):
        self.put('ok.vq', 'int x = 1;')
        self.assertEqual(self.triage()[0]['category'], 'REVIEW_PASS')

    def test_error_not_approved(self):
        self.put('bad.vq', 'int x = missing;')
        self.assertEqual(self.triage()[0]['category'], 'REVIEW_ERROR')

    def test_changed_hash(self):
        p = self.put('ok.vq', 'int x = 1;')
        candidate = candidate_baseline(self.root)
        p.write_text('int x = 2;', encoding='utf-8')
        self.assertEqual(classify_candidate(candidate, self.root)[0]['category'], 'CHANGED')

    def test_missing_file(self):
        p = self.put('ok.vq', 'int x = 1;')
        candidate = candidate_baseline(self.root)
        p.unlink()
        self.assertEqual(classify_candidate(candidate, self.root)[0]['category'], 'CHANGED')

    def test_internal_failure(self):
        self.put('ok.vq', 'int x = 1;')
        candidate = candidate_baseline(self.root)
        candidate['cases']['ok.vq']['observed'] = {'borrow': 'AUDIT_ERROR', 'code': 'BORROW_INTERNAL_ERROR'}
        self.assertEqual(classify_candidate(candidate, self.root)[0]['category'], 'INTERNAL_FAILURE')

    def test_unsupported(self):
        self.put('ok.vq', 'int x = 1;')
        candidate = candidate_baseline(self.root)
        candidate['cases']['ok.vq']['observed'] = {'borrow': 'UNSUPPORTED', 'code': 'UNSUPPORTED_CONSTRUCT'}
        self.assertEqual(classify_candidate(candidate, self.root)[0]['category'], 'ANALYZER_GAP')

    def test_root_mismatch(self):
        self.put('ok.vq', 'int x = 1;')
        with self.assertRaisesRegex(ValueError, 'mismatch'):
            classify_candidate(candidate_baseline(self.root), self.root / 'wrong')

    def test_path_traversal(self):
        self.put('ok.vq', 'int x = 1;')
        candidate = candidate_baseline(self.root)
        candidate['cases']['../outside.vq'] = candidate['cases'].pop('ok.vq')
        with self.assertRaisesRegex(ValueError, 'Unsafe'):
            classify_candidate(candidate, self.root)

    def test_summary(self):
        self.put('ok.vq', 'int x = 1;')
        self.put('bad.vq', 'int x = missing;')
        self.assertEqual(triage_summary(self.triage()), {'REVIEW_ERROR': 1, 'REVIEW_PASS': 1})

    def test_empty(self):
        self.assertEqual(self.triage(), [])


if __name__ == '__main__':
    unittest.main()
