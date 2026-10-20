"""Bounded, opt-in source borrow diagnostics and QRVM IR parity audit.

Parity compares direct AST against AST->IR->AST QRVM paths, NOT QuarC.
"""
from dataclasses import dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from qrvm.borrow_gate import check_borrow_source
from tools.ir_runtime_audit import audit_runtime_file


@dataclass(frozen=True)
class AuditRow:
    path: str
    borrow_status: str
    borrow_code: str
    parity_status: str
    detail: str


def audit_sources(paths, *, run_parity=False, max_files=250):
    """Return ordered rows. No source is executed unless run_parity=True.

    Parity uses the existing isolated, timeout-bounded QRVM auditor.
    """
    if max_files < 1:
        raise ValueError('max_files must be positive')
    ordered = sorted({Path(path).resolve() for path in paths})
    if len(ordered) > max_files:
        raise ValueError(f'File limit exceeded: {len(ordered)} > {max_files}')
    rows = []
    for path in ordered:
        try:
            source = path.read_text(encoding='utf-8')
        except (OSError, UnicodeError) as exc:
            rows.append(AuditRow(str(path), 'ERROR', 'SOURCE_READ_ERROR', 'NOT_RUN', str(exc)))
            continue
        try:
            diagnostic = check_borrow_source(source)
            borrow_status = diagnostic.status.value
            borrow_code = diagnostic.code
            detail = diagnostic.message
        except Exception as exc:
            # An unexpected analyzer failure is an audit failure, not UNSUPPORTED.
            borrow_status = 'AUDIT_ERROR'
            borrow_code = 'BORROW_INTERNAL_ERROR'
            detail = f'{type(exc).__name__}: {exc}'
        parity = 'NOT_RUN'
        if run_parity:
            try:
                parity, parity_detail = audit_runtime_file(path)
                if parity_detail:
                    detail += f' | parity: {parity_detail}'
            except Exception as exc:
                parity = 'audit_error'
                detail += f' | parity: {type(exc).__name__}: {exc}'
        rows.append(AuditRow(str(path), borrow_status, borrow_code, parity, detail))
    return tuple(rows)


def discover_sources(root):
    """Discover .vq files, excluding interactive input folders."""
    root = Path(root)
    return tuple(sorted(p for p in root.rglob('*.vq') if 'input' not in p.relative_to(root).parts))


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path, help='Directory containing .vq files')
    parser.add_argument('--parity', action='store_true', help='Run isolated QRVM AST/IR parity checks')
    parser.add_argument('--max-files', type=int, default=250)
    parser.add_argument('--expect', type=Path, help='JSON manifest of expected outcomes')
    parser.add_argument('--strict-unclassified', action='store_true', help='Fail when a source has no expectation')
    args = parser.parse_args(argv)
    rows = audit_sources(discover_sources(args.root), run_parity=args.parity, max_files=args.max_files)
    from collections import Counter
    for row in rows:
        print(f'{Path(row.path).name}: {row.borrow_status} [{row.borrow_code}] / {row.parity_status}')
    print(f'Files: {len(rows)}; borrow: {dict(Counter(row.borrow_status for row in rows))}; parity: {dict(Counter(row.parity_status for row in rows))}')
    if args.expect is not None:
        from tools.borrow_expectations import load_expectations, classify_rows
        expectations = load_expectations(args.expect)
        classified = classify_rows(rows, args.root, expectations)
        from collections import Counter
        for item in classified:
            print(f'{Path(item.path).name}: {item.classification} ({item.reason})')
        counts = Counter(item.classification for item in classified)
        print('; '.join(f'{key}: {counts[key]}' for key in ('EXPECTED', 'UNEXPECTED', 'UNCLASSIFIED')))
        if counts['UNEXPECTED'] or (args.strict_unclassified and counts['UNCLASSIFIED']):
            return 1
    failures = {'AUDIT_ERROR'}
    parity_failures = {'runtime_mismatch', 'bytecode_mismatch', 'compile_error_mismatch', 'audit_error', 'worker_error'}
    return 1 if any(row.borrow_status in failures or row.parity_status in parity_failures for row in rows) else 0


if __name__ == '__main__':
    raise SystemExit(main())
