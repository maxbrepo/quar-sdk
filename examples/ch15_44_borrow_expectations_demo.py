"""Run the expected-outcome audit against a temporary positive/negative corpus."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / 'valid.vq').write_text('int x = 1;', encoding='utf-8')
        (root / 'invalid.vq').write_text('int x = missing;', encoding='utf-8')
        manifest = root / 'expected.json'
        manifest.write_text(json.dumps({'version': 1, 'cases': {
            'valid.vq': {'borrow': 'PASS', 'code': 'BORROW_PASS'},
            'invalid.vq': {'borrow': 'ERROR', 'code': 'BORROW_ERROR'},
        }}), encoding='utf-8')
        result = subprocess.run([sys.executable, str(ROOT / 'tools/borrow_regression_audit.py'),
                                 str(root), '--expect', str(manifest)], capture_output=True, text=True)
        print(result.stdout, end='')
        if result.returncode or 'EXPECTED: 2' not in result.stdout:
            print(result.stderr, file=sys.stderr)
            raise SystemExit('FAIL: expectation audit')
        print('PASS: positive and intentional-negative expectations')


if __name__ == '__main__':
    main()
