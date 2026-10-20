"""Demonstrate explicit pure-call trust without changing compiler defaults."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from qrvm.borrow_gate import check_borrow_source

source = 'int x = 1; int y = foo(x);'
unknown = check_borrow_source(source)
trusted = check_borrow_source(source, pure_calls=('foo',))
missing = check_borrow_source('int y = foo(missing);', pure_calls=('foo',))
print(f'unknown effects: {unknown.status.value} [{unknown.code}]')
print(f'explicitly trusted: {trusted.status.value} [{trusted.code}]')
print(f'missing argument: {missing.status.value} [{missing.code}]')
assert (unknown.status.value, trusted.status.value, missing.status.value) == ('UNSUPPORTED', 'PASS', 'ERROR')
print('PASS: conservative function-call argument analysis')
