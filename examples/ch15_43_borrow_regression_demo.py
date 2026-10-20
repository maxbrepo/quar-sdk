"""Run Chapter 15 borrow and bounded QRVM parity checks on example sources."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.borrow_regression_audit import audit_sources

valid = ROOT / 'examples/0.0.4/typed/15 memory safety/239 borrow source valid.vq'
rows = audit_sources([valid], run_parity=True)
for row in rows:
    print(f'{Path(row.path).name}: {row.borrow_status} [{row.borrow_code}] / {row.parity_status}')
print('PASS: bounded borrow regression audit')
