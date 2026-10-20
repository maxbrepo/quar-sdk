"""Runnable analysis demo; not Visual Quar source syntax.

Run from SDK root: python3 examples/ch15_33_borrow_lifetime_demo.py
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from qrvm.borrow_lifetime import BorrowLifetimeState
from qrvm.borrow_access import BorrowMode
from qrvm.ownership_analysis import OwnershipError

state = BorrowLifetimeState.empty().declare('buffer')
state = state.enter('processing')
state = state.borrow('buffer', 'reader')
state.read('reader')
try:
    state.write('buffer')
except OwnershipError as error:
    print('Expected conflict:', error)
state = state.release('reader')
state = state.borrow('buffer', 'writer', BorrowMode.MUTABLE)
state.write('writer')
state = state.exit()
state.write('buffer')
print('PASS: shared/mutable borrow and scope expiration')
