"""Demonstrate candidate versus explicitly approved borrow expectations."""
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.borrow_baseline import approve_baseline, candidate_baseline

with tempfile.TemporaryDirectory() as folder:
    root = Path(folder)
    (root / 'valid.vq').write_text('int x = 1;', encoding='utf-8')
    (root / 'invalid.vq').write_text('int x = missing;', encoding='utf-8')
    candidate = candidate_baseline(root)
    print(f'Candidate: {len(candidate["cases"])} unapproved sources')
    approved = approve_baseline(candidate, root, ['valid.vq'])
    print(f'Approved: {len(approved["cases"])} reviewed source')
    assert 'invalid.vq' not in approved['cases']
    print('PASS: no automatic approval of observed errors')
