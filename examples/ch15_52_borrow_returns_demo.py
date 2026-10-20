"""Demonstrate conservative return-value analysis."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from qrvm.borrow_returns import summarize_source_returns
from qrvm.borrow_gate import check_borrow_source

safe = 'int increment(int x) { return x + 1; } int y = increment(2);'
unknown = 'int incomplete(int x) { int y = x; } int z = incomplete(2);'
summary = summarize_source_returns(safe)[0]
print(f'{summary.name}: {summary.classification}')
assert summary.classification == 'SCALAR_VALUE'
assert check_borrow_source(safe, infer_local_calls=True).status.value == 'PASS'
result = check_borrow_source(unknown, infer_local_calls=True)
print(f'incomplete return: {result.status.value}')
assert result.status.value == 'UNSUPPORTED'
print('PASS: conservative scalar return analysis')
