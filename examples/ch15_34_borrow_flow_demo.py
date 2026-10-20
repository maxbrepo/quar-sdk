"""Run from SDK root: python3 examples/ch15_34_borrow_flow_demo.py"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from qrvm.borrow_flow import BorrowFlow
from qrvm.ownership_analysis import OwnershipError

flow = BorrowFlow.empty().declare('item').enter('conditional')
flow = flow.branch(lambda path: path.borrow('item', 'ref'), lambda path: path)
try:
    flow.write('item')
except OwnershipError as error:
    print('Expected branch conflict:', error)
else:
    raise AssertionError('Unsafe branch write was accepted')
flow = flow.exit()
flow.write('item')
print('PASS: conditional borrow expires at scope exit')
