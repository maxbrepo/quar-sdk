"""Inspect local function effects without automatically trusting calls."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from qrvm.borrow_effects import summarize_source_effects
from qrvm.borrow_gate import check_borrow_source

source = 'int increment(int x) { return x + 1; }'
effect = summarize_source_effects(source)[0]
print(f'{effect.name}: {effect.classification}')
assert effect.classification == 'LOCAL_READ_ONLY'
unknown = check_borrow_source('int y = increment(1);')
print(f'call without explicit trust: {unknown.status.value}')
assert unknown.status.value == 'UNSUPPORTED'
print('PASS: conservative function effect summary')
