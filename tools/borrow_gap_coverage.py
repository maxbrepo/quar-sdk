"""Read-only coverage report for unsupported borrow-checker constructs."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from qrvm.borrow_gate import check_borrow_source
from tools.borrow_triage import classify_candidate


def gap_coverage(candidate, root, *, limit=20):
    """Recheck unchanged unsupported sources and group their diagnostics.

    Returns an observation report only; no source or baseline is modified.
    """
    if limit < 1:
        raise ValueError('limit must be positive')
    root = Path(root).resolve()
    rows = classify_candidate(candidate, root)
    gaps = []
    stale = []
    counts = Counter(row['category'] for row in rows)
    for row in rows:
        if row['category'] != 'ANALYZER_GAP':
            continue
        path = (root / row['path']).resolve()
        entry = candidate['cases'][row['path']]
        # Recheck the hash immediately before reading, to avoid stale conclusions.
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != entry['sha256']:
            stale.append(row['path'])
            continue
        try:
            diagnostic = check_borrow_source(content.decode('utf-8'))
        except Exception as exc:
            # Unexpected failures must be visible, not treated as unsupported.
            gaps.append({'path': row['path'], 'category': 'INTERNAL_FAILURE', 'reason': type(exc).__name__})
            continue
        if diagnostic.status.value != 'UNSUPPORTED':
            stale.append(row['path'])
            continue
        gaps.append({'path': row['path'], 'category': 'ANALYZER_GAP', 'reason': diagnostic.message})
    reasons = Counter(row['reason'] for row in gaps if row['category'] == 'ANALYZER_GAP')
    grouped = [{'reason': reason, 'count': count} for reason, count in sorted(reasons.items(), key=lambda item: (-item[1], item[0]))]
    return {
        'version': 1,
        'total': len(rows),
        'summary': dict(sorted(counts.items())),
        'unsupported': counts['ANALYZER_GAP'],
        'reanalyzed': len(gaps),
        'stale': sorted(stale),
        'groups': grouped,
        'examples': sorted(gaps, key=lambda row: row['path'])[:limit],
        'approved': 0,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('--root', type=Path)
    parser.add_argument('--limit', type=int, default=20)
    parser.add_argument('--json-output', type=Path)
    args = parser.parse_args(argv)
    candidate = json.loads(args.candidate.read_text(encoding='utf-8'))
    root = args.root if args.root is not None else Path(candidate['root'])
    report = gap_coverage(candidate, root, limit=args.limit)
    print(f"Files: {report['total']}; unsupported: {report['unsupported']}; reanalyzed: {report['reanalyzed']}; stale: {len(report['stale'])}")
    for group in report['groups']:
        print(f"GAP x{group['count']}: {group['reason']}")
    for row in report['examples']:
        print(f"{row['category']}: {row['path']}")
    if args.json_output:
        args.json_output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return 1 if report['stale'] or any(row['category'] == 'INTERNAL_FAILURE' for row in report['examples']) else 0


if __name__ == '__main__':
    raise SystemExit(main())
