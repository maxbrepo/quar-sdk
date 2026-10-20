"""Generate review-only borrow baselines; never approve observed outcomes implicitly."""
import argparse
import hashlib
import json
from pathlib import Path

import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.borrow_regression_audit import audit_sources, discover_sources
from tools.borrow_expectations import load_expectations


def candidate_baseline(root, *, max_files=500):
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError('Audit root must be a directory')
    entries = {}
    for row in audit_sources(discover_sources(root), max_files=max_files):
        path = Path(row.path)
        relative = path.relative_to(root).as_posix()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        entries[relative] = {
            'sha256': digest,
            'observed': {'borrow': row.borrow_status, 'code': row.borrow_code},
            'reviewed': False,
        }
    return {'version': 1, 'root': str(root), 'cases': entries}


def approve_baseline(candidate, root, reviewed_paths):
    """Produce expectations only for explicitly reviewed, unchanged, non-internal outcomes."""
    root = Path(root).resolve()
    if candidate.get('version') != 1 or candidate.get('root') != str(root):
        raise ValueError('Candidate root/version mismatch')
    cases = candidate.get('cases')
    if not isinstance(cases, dict):
        raise ValueError('Invalid candidate cases')
    reviewed = set(reviewed_paths)
    if not reviewed or reviewed - cases.keys():
        raise ValueError('Review list empty or contains unknown sources')
    approved = {}
    for name in sorted(reviewed):
        path = Path(name)
        if path.is_absolute() or '..' in path.parts or '\\' in name:
            raise ValueError('Unsafe source path')
        full = (root / path).resolve()
        if not full.is_relative_to(root) or not full.is_file():
            raise ValueError('Missing or outside source')
        entry = cases[name]
        if hashlib.sha256(full.read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError(f'Source changed since audit: {name}')
        observed = entry['observed']
        if observed['borrow'] in {'AUDIT_ERROR'} or observed['code'] in {'BORROW_INTERNAL_ERROR', 'SOURCE_READ_ERROR'}:
            raise ValueError(f'Cannot approve internal audit failure: {name}')
        approved[name] = dict(observed)
    return {'version': 1, 'cases': approved}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--candidate', required=True, type=Path)
    parser.add_argument('--max-files', type=int, default=500)
    parser.add_argument('--reviewed-list', type=Path, help='UTF-8 file containing one reviewed relative .vq path per line')
    parser.add_argument('--output', type=Path, help='Write approved expectations; requires --reviewed-list')
    args = parser.parse_args(argv)
    if bool(args.reviewed_list) != bool(args.output):
        parser.error('--reviewed-list and --output must be supplied together')
    if args.reviewed_list:
        candidate = json.loads(args.candidate.read_text(encoding='utf-8'))
        reviewed = [line.strip() for line in args.reviewed_list.read_text(encoding='utf-8').splitlines() if line.strip() and not line.lstrip().startswith('#')]
        approved = approve_baseline(candidate, args.root, reviewed)
        args.output.write_text(json.dumps(approved, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        load_expectations(args.output)
        print(f'Approved: {len(approved["cases"])} reviewed cases')
    else:
        candidate = candidate_baseline(args.root, max_files=args.max_files)
        args.candidate.write_text(json.dumps(candidate, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        from collections import Counter
        statuses = Counter(v['observed']['borrow'] for v in candidate['cases'].values())
        print(f'Candidate: {len(candidate["cases"])} unapproved cases; observed: {dict(statuses)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
