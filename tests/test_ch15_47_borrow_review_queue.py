import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from tools.borrow_review_queue import build_review_queue, main


class BorrowReviewQueueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cases = {}

    def add(self, name, status, code='BORROW_PASS'):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('int value = 1;\n', encoding='utf-8')
        self.cases[name] = {
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'observed': {'borrow': status, 'code': code},
            'reviewed': False,
        }

    def candidate(self):
        return {'version': 1, 'root': str(self.root.resolve()), 'cases': self.cases}

    def test_empty(self):
        report = build_review_queue(self.candidate(), self.root)
        self.assertEqual(report['total'], 0)
        self.assertEqual(report['remaining'], 0)

    def test_pass_unapproved(self):
        self.add('a.vq', 'PASS')
        report = build_review_queue(self.candidate(), self.root)
        self.assertEqual(report['queue'][0]['category'], 'REVIEW_PASS')
        self.assertEqual(report['approved'], 0)

    def test_error_precedes_pass(self):
        self.add('a.vq', 'PASS')
        self.add('b.vq', 'ERROR', 'BORROW_ERROR')
        self.assertEqual(build_review_queue(self.candidate(), self.root)['queue'][0]['path'], 'b.vq')

    def test_gap_precedes_pass(self):
        self.add('a.vq', 'PASS')
        self.add('b.vq', 'UNSUPPORTED', 'UNSUPPORTED_CONSTRUCT')
        self.assertEqual(build_review_queue(self.candidate(), self.root)['queue'][0]['category'], 'ANALYZER_GAP')

    def test_internal_first(self):
        self.add('a.vq', 'ERROR')
        self.add('b.vq', 'AUDIT_ERROR', 'BORROW_INTERNAL_ERROR')
        self.assertEqual(build_review_queue(self.candidate(), self.root)['queue'][0]['category'], 'INTERNAL_FAILURE')

    def test_changed_first_after_internal(self):
        self.add('a.vq', 'PASS')
        self.add('b.vq', 'ERROR')
        (self.root / 'a.vq').write_text('changed', encoding='utf-8')
        self.assertEqual(build_review_queue(self.candidate(), self.root)['queue'][0]['category'], 'CHANGED')

    def test_missing_changed(self):
        self.add('a.vq', 'PASS')
        (self.root / 'a.vq').unlink()
        self.assertEqual(build_review_queue(self.candidate(), self.root)['summary']['CHANGED'], 1)

    def test_limit(self):
        for i in range(4):
            self.add(f'{i}.vq', 'PASS')
        report = build_review_queue(self.candidate(), self.root, limit=2)
        self.assertEqual((len(report['queue']), report['remaining'], report['total']), (2, 2, 4))

    def test_invalid_limit(self):
        with self.assertRaises(ValueError):
            build_review_queue(self.candidate(), self.root, limit=0)

    def test_deterministic_order(self):
        self.add('z.vq', 'PASS')
        self.add('a.vq', 'PASS')
        self.assertEqual([x['path'] for x in build_review_queue(self.candidate(), self.root)['queue']], ['a.vq', 'z.vq'])

    def test_cli_json(self):
        self.add('a.vq', 'PASS')
        source = self.root / 'candidate.json'
        output = self.root / 'report.json'
        source.write_text(json.dumps(self.candidate()), encoding='utf-8')
        self.assertEqual(main([str(source), '--json-output', str(output)]), 0)
        self.assertEqual(json.loads(output.read_text())['total'], 1)

    def test_cli_fails_on_internal(self):
        self.add('a.vq', 'AUDIT_ERROR', 'BORROW_INTERNAL_ERROR')
        source = self.root / 'candidate.json'
        source.write_text(json.dumps(self.candidate()), encoding='utf-8')
        self.assertEqual(main([str(source)]), 1)


if __name__ == '__main__':
    unittest.main()
