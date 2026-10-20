"""Show a safe, read-only report of analyzer coverage gaps."""
import hashlib
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.borrow_gap_coverage import gap_coverage


def main():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp).resolve()
        source = root / 'valid.vq'
        source.write_text('int value = 1;\n', encoding='utf-8')
        candidate = {'version': 1, 'root': str(root), 'cases': {
            'valid.vq': {'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                         'observed': {'borrow': 'PASS', 'code': 'BORROW_PASS'}, 'reviewed': False}
        }}
        report = gap_coverage(candidate, root)
        assert report['total'] == 1 and report['unsupported'] == 0
        assert report['approved'] == 0
        print('Files: 1; unsupported: 0; approved: 0')
        print('PASS: read-only coverage report')


if __name__ == '__main__':
    main()
