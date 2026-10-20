"""Produce a reproducible Chapter 13 IR parity and limitation report."""
from collections import Counter
from pathlib import Path
import argparse
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.ir_runtime_audit import ROOT, audit_runtime_file, classify_audit_result

KNOWN_LIMITATIONS = {
    '002 function.vq': 'parser_failure',
    '103 named arguments.vq': 'named_arguments_not_compiled',
    '104 positional and named arguments.vq': 'named_arguments_not_compiled',
    '106 unknown named argument error.vq': 'named_argument_negative_not_validated',
    '107 duplicate named argument error.vq': 'named_argument_negative_not_validated',
    '108 positional after named error.vq': 'named_argument_negative_not_validated',
    '227 assertion wrong arity error.vq': 'assert_diagnostic_not_validated',
    '233 panic wrong arity error.vq': 'panic_diagnostic_not_validated',
}


def collect_report(root):
    """Audit every source and return measured counts plus unresolved limitations."""
    counts = Counter()
    limitations = []
    regressions = []
    paths = sorted(root.rglob('*.vq'))
    for path in paths:
        status, detail = audit_runtime_file(path)
        counts[status] += 1
        classification = classify_audit_result(path, status)
        if classification == 'regression':
            regressions.append((str(path.relative_to(root)), status, detail))
        if path.name in KNOWN_LIMITATIONS and classification not in ('verified_equivalent', 'module_fixture'):
            limitations.append((str(path.relative_to(root)), KNOWN_LIMITATIONS[path.name], status))
    return len(paths), counts, limitations, regressions


def render_report(total, counts, limitations, regressions):
    """Format an auditable report; parity is not conflated with correctness."""
    lines = [
        '# Visual Quar 0.0.4 — Chapter 13B IR parity report', '',
        'Generated from the current local corpus; not a certification of language correctness.', '',
        f'Total source files: **{total}**', '',
        '| Measured outcome | Files |', '|---|---:|',
    ]
    lines += [f'| `{status}` | {count} |' for status, count in sorted(counts.items())]
    lines += ['', f'Unexpected IR-path regressions: **{len(regressions)}**.', '',
              '## Known limitations requiring separate language/runtime validation', '']
    for path, limitation, status in limitations:
        lines.append(f'- `{path}` — {limitation} (`{status}`).')
    if not limitations:
        lines.append('No known limitations found in this corpus.')
    lines += ['', '## Interpretation', '',
              '- `runtime_equal` means observable behavior matched the legacy pipeline under the audit environment.',
              '- `compile_error_equal` means both routes rejected a source, **not** that rejection was correct.',
              '- Parsing and module-loading failures happen before IR parity can be assessed.',
              '- Timeouts require an independently specified expected outcome.',
              '- The IR-to-bytecode route currently uses an IR-to-AST adapter; direct IR bytecode generation is not implemented.',
              '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT / 'examples')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = collect_report(args.root)
    report = render_report(*result)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding='utf-8')
    else:
        print(report)
    return 1 if result[3] else 0


if __name__ == '__main__':
    raise SystemExit(main())
