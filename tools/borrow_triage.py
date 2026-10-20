"""Read-only triage of unapproved borrow baseline observations."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


ALLOWED = {'PASS', 'ERROR', 'UNSUPPORTED', 'AUDIT_ERROR'}


def classify_candidate(candidate, root):
    """Classify observations, never infer that an observed error is expected."""
    root = Path(root).resolve()
    if candidate.get('version') != 1 or candidate.get('root') != str(root):
        raise ValueError('Candidate version/root mismatch')
    cases = candidate.get('cases')
    if not isinstance(cases, dict):
        raise ValueError('Invalid candidate cases')
    rows = []
    for name, entry in sorted(cases.items()):
        if not isinstance(name, str) or not name.endswith('.vq') or '\\' in name:
            raise ValueError('Invalid source name')
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Unsafe source path')
        path = (root / relative).resolve()
        if not path.is_relative_to(root):
            raise ValueError('Source escapes root')
        if not isinstance(entry, dict) or not isinstance(entry.get('observed'), dict):
            raise ValueError('Invalid candidate entry')
        observed = entry['observed']
        status, code = observed.get('borrow'), observed.get('code')
        if status not in ALLOWED or not isinstance(code, str):
            raise ValueError('Invalid observation')
        if not path.is_file():
            category = 'CHANGED'
            reason = 'source missing'
        elif hashlib.sha256(path.read_bytes()).hexdigest() != entry.get('sha256'):
            category = 'CHANGED'
            reason = 'source hash changed'
        elif status == 'PASS':
            category, reason = 'REVIEW_PASS', 'checks passed; not approved'
        elif status == 'UNSUPPORTED':
            category, reason = 'ANALYZER_GAP', 'unsupported analysis'
        elif status == 'ERROR':
            category, reason = 'REVIEW_ERROR', 'error may be intentional or a regression'
        else:
            category, reason = 'INTERNAL_FAILURE', 'unexpected analyzer failure'
        rows.append({'path': name, 'category': category, 'borrow': status, 'code': code, 'reason': reason})
    return rows


def triage_summary(rows):
    return dict(sorted(Counter(row['category'] for row in rows).items()))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate', type=Path, help='Unapproved candidate JSON from borrow_baseline.py')
    parser.add_argument('--root', type=Path, help='Source root; defaults to root recorded in candidate')
    parser.add_argument('--json-output', type=Path, help='Optional JSON report (does not approve cases)')
    args = parser.parse_args(argv)
    candidate = json.loads(args.candidate.read_text(encoding='utf-8'))
    root = args.root if args.root is not None else Path(candidate['root'])
    rows = classify_candidate(candidate, root)
    for row in rows:
        print(f"{row['path']}: {row['category']} [{row['code']}]")
    counts = triage_summary(rows)
    print(f'Files: {len(rows)}; triage: {counts}')
    if args.json_output is not None:
        args.json_output.write_text(json.dumps({'version': 1, 'summary': counts, 'rows': rows}, indent=2) + '\n', encoding='utf-8')
    return 1 if counts.get('CHANGED', 0) or counts.get('INTERNAL_FAILURE', 0) else 0


if __name__ == '__main__':
    raise SystemExit(main())
