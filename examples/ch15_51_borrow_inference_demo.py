"""Opt-in function inference demonstration."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from qrvm.borrow_gate import check_borrow_source

source = 'int increment(int x) { return x + 1; } int y = increment(2);'
for enabled in (False, True):
    result = check_borrow_source(source, infer_local_calls=enabled)
    print(f'inference={enabled}: {result.status.value} [{result.code}]')
    assert result.status.value == ('PASS' if enabled else 'UNSUPPORTED')
print('PASS: conservative opt-in function inference')
