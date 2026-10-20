"""Build a deterministic, read-only review queue from a borrow baseline candidate."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.borrow_triage import classify_candidate

PRIORITY = ('INTERNAL_FAILURE', 'CHANGED', 'REVIEW_ERROR', 'ANALYZER_GAP', 'REVIEW_PASS')


def build_review_queue(candidate, root, *, limit=25):
    """Return all category counts and a bounded queue; never approve observations."""
    if limit < 1:
        raise ValueError('limit must be positive')
    rows = classify_candidate(candidate, root)
    rank = {category: index for index, category in enumerate(PRIORITY)}
    ordered = sorted(rows, key=lambda row: (rank[row['category']], row['path']))
    counts = Counter(row['category'] for row in rows)
    return {
        'version': 1,
        'total': len(rows),
        'summary': {category: counts[category] for category in PRIORITY},
        'remaining': max(0, len(rows) - limit),
        'queue': ordered[:limit],
        'approved': 0,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('--root', type=Path, help='Override root recorded in candidate')
    parser.add_argument('--limit', type=int, default=25)
    parser.add_argument('--json-output', type=Path)
    args = parser.parse_args(argv)
    candidate = json.loads(args.candidate.read_text(encoding='utf-8'))
    root = args.root if args.root is not None else Path(candidate['root'])
    report = build_review_queue(candidate, root, limit=args.limit)
    for row in report['queue']:
        print(f"{row['category']}: {row['path']} [{row['code']}]")
    print(f"Files: {report['total']}; review: {report['summary']}; queued: {len(report['queue'])}; remaining: {report['remaining']}")
    if args.json_output is not None:
        args.json_output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return 1 if report['summary']['INTERNAL_FAILURE'] or report['summary']['CHANGED'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
