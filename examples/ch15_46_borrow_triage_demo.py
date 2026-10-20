"""Run review-only triage on a small temporary Visual Quar source library."""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.borrow_baseline import candidate_baseline
from tools.borrow_triage import classify_candidate, triage_summary

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    (root / 'valid.vq').write_text('int x = 1;', encoding='utf-8')
    (root / 'invalid.vq').write_text('int x = missing;', encoding='utf-8')
    rows = classify_candidate(candidate_baseline(root), root)
    for row in rows:
        print(f"{row['path']}: {row['category']}")
    assert triage_summary(rows) == {'REVIEW_ERROR': 1, 'REVIEW_PASS': 1}
    print('PASS: observations classified without automatic approval')
