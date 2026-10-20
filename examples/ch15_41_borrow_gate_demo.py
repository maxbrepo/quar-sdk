"""Run the opt-in borrow gate against real Visual Quar source snippets."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from qrvm.borrow_gate import check_borrow_source
from main import build_frontend

cases = (
    ('valid', 'int x = 1; int y = x;'),
    ('invalid', 'if (true) { int temp = 1; } int x = temp;'),
    ('unsupported', 'print(1);'),
)
for name, source in cases:
    result = check_borrow_source(source)
    print(f'{name}: {result.status.value}')

build_frontend('int x = 1;', borrow_check=True)
print('PASS: opt-in frontend borrow gate')
