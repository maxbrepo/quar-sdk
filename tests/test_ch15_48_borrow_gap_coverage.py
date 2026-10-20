import hashlib
from pathlib import Path
import tempfile
import unittest

from tools.borrow_gap_coverage import gap_coverage


class GapCoverageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.cases = {}

    def add(self, name, content, status='UNSUPPORTED', code='UNSUPPORTED_CONSTRUCT'):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
        self.cases[name] = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'observed': {'borrow': status, 'code': code}, 'reviewed': False}

    def report(self, **kwargs):
        return gap_coverage({'version': 1, 'root': str(self.root), 'cases': self.cases}, self.root, **kwargs)

    def test_empty(self):
        self.assertEqual(self.report()['total'], 0)

    def test_pass_not_rechecked(self):
        self.add('valid.vq', 'int x = 1;', 'PASS', 'BORROW_PASS')
        self.assertEqual(self.report()['reanalyzed'], 0)

    def test_stale_changed_source(self):
        self.add('a.vq', 'int x = 1;')
        (self.root / 'a.vq').write_text('int y = 2;')
        self.assertEqual(self.report()['summary']['CHANGED'], 1)

    def test_reanalysis_no_longer_unsupported(self):
        self.add('a.vq', 'int x = 1;')
        self.assertEqual(self.report()['stale'], ['a.vq'])

    def test_actual_unsupported_construct(self):
        self.add('call.vq', 'print(1);')
        report = self.report()
        self.assertEqual(report['unsupported'], 1)
        self.assertEqual(report['reanalyzed'], 1)
        self.assertIn('FunctionCall', report['groups'][0]['reason'])

    def test_groups_repeated_constructs(self):
        self.add('a.vq', 'print(1);')
        self.add('b.vq', 'print(2);')
        report = self.report(limit=1)
        self.assertEqual(report['groups'][0]['count'], 2)
        self.assertEqual(len(report['examples']), 1)

    def test_invalid_limit(self):
        with self.assertRaises(ValueError):
            self.report(limit=0)

    def test_no_approval(self):
        self.assertEqual(self.report()['approved'], 0)

    def test_root_mismatch(self):
        with self.assertRaises(ValueError):
            gap_coverage({'version': 1, 'root': '/wrong', 'cases': {}}, self.root)

    def test_missing_source(self):
        self.add('a.vq', 'int x = 1;')
        (self.root / 'a.vq').unlink()
        self.assertEqual(self.report()['summary']['CHANGED'], 1)

    def test_reject_escape(self):
        self.add('a.vq', 'int x = 1;')
        self.cases['../bad.vq'] = self.cases.pop('a.vq')
        with self.assertRaises(ValueError):
            self.report()

    def test_reject_nonpositive_limit(self):
        with self.assertRaises(ValueError):
            self.report(limit=-5)


if __name__ == '__main__':
    unittest.main()
