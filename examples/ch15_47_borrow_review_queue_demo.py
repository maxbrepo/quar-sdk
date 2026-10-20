"""Demonstrate review prioritization without approving any observed result."""
import hashlib
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.borrow_review_queue import build_review_queue


def main():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        cases = {}
        for name, status, code in (
            ('valid.vq', 'PASS', 'BORROW_PASS'),
            ('invalid.vq', 'ERROR', 'BORROW_ERROR'),
            ('unsupported.vq', 'UNSUPPORTED', 'UNSUPPORTED_CONSTRUCT'),
        ):
            path = root / name
            path.write_text('int value = 1;\n', encoding='utf-8')
            cases[name] = {
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                'observed': {'borrow': status, 'code': code},
                'reviewed': False,
            }
        report = build_review_queue({'version': 1, 'root': str(root), 'cases': cases}, root)
        for row in report['queue']:
            print(f"{row['path']}: {row['category']}")
        assert report['approved'] == 0
        assert report['queue'][0]['category'] == 'REVIEW_ERROR'
        print('PASS: prioritized review without automatic approval')


if __name__ == '__main__':
    main()
