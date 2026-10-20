"""Expected-outcome manifest for the opt-in borrow regression audit.

The manifest is JSON: {"version": 1, "cases": {"relative/file.vq":
{"borrow": "PASS", "code": "BORROW_PASS", "parity": "runtime_equal"}}}.
"""
import json
from dataclasses import dataclass
from pathlib import Path

ALLOWED_BORROW = frozenset({'PASS', 'ERROR', 'UNSUPPORTED', 'AUDIT_ERROR'})


@dataclass(frozen=True)
class ClassifiedRow:
    path: str
    classification: str
    reason: str


def load_expectations(path):
    """Validate a manifest without executing or importing user-controlled code."""
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(payload, dict) or payload.get('version') != 1 or not isinstance(payload.get('cases'), dict):
        raise ValueError('Expected manifest with version=1 and cases object')
    result = {}
    for name, expected in payload['cases'].items():
        if not isinstance(name, str) or not name or Path(name).is_absolute() or '..' in Path(name).parts or '\\' in name:
            raise ValueError(f'Unsafe manifest path: {name!r}')
        if not isinstance(expected, dict) or not expected or set(expected) - {'borrow', 'code', 'parity'}:
            raise ValueError(f'Invalid expectations for {name!r}')
        if 'borrow' in expected and expected['borrow'] not in ALLOWED_BORROW:
            raise ValueError(f'Invalid borrow expectation for {name!r}')
        if any(not isinstance(value, str) or not value for value in expected.values()):
            raise ValueError(f'Invalid expectation value for {name!r}')
        result[Path(name).as_posix()] = expected
    return result


def classify_rows(rows, root, expectations):
    """Compare actual outcomes with declared expectations; do not infer intent."""
    root = Path(root).resolve()
    results = []
    for row in rows:
        path = Path(row.path).resolve()
        try:
            name = path.relative_to(root).as_posix()
        except ValueError:
            results.append(ClassifiedRow(str(path), 'UNEXPECTED', 'Source outside audit root'))
            continue
        expected = expectations.get(name)
        if expected is None:
            results.append(ClassifiedRow(str(path), 'UNCLASSIFIED', 'No expected outcome declared'))
            continue
        actual = {'borrow': row.borrow_status, 'code': row.borrow_code, 'parity': row.parity_status}
        differences = [f'{field}: expected {value}, got {actual[field]}' for field, value in expected.items() if actual[field] != value]
        if row.borrow_status == 'AUDIT_ERROR' or row.parity_status in {'audit_error', 'worker_error'}:
            differences.append('Internal audit failure')
        results.append(ClassifiedRow(str(path), 'UNEXPECTED' if differences else 'EXPECTED', '; '.join(differences) if differences else 'Matches manifest'))
    return tuple(results)
