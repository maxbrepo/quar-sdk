"""Runnable demonstration of finite-state borrow-flow loop closure."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qrvm.borrow_flow import BorrowFlow
from qrvm.borrow_fixpoint import loop_fixpoint
from qrvm.ownership_analysis import OwnershipError


def body(flow):
    state = flow.paths[0]
    if 'ref' in state.modes:
        return flow.release('ref')
    return flow.borrow('value', 'ref')


def main():
    start = BorrowFlow.empty().declare('value')
    result = loop_fixpoint(start, body)
    assert result.reachable_states == 2
    try:
        result.flow.write('value')
    except OwnershipError as error:
        print('Expected loop conflict:', error)
    else:
        raise AssertionError('Expected a conflicting borrow')
    print('PASS: loop fixpoint converged across repeated borrow/release states')


if __name__ == '__main__':
    main()
