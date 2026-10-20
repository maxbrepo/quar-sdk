"""Tests for explicit shared and mutable borrow access rules."""
import unittest
from qrvm.borrow_access import BorrowAccessState, BorrowMode
from qrvm.ownership_analysis import OwnershipError


class BorrowAccessTests(unittest.TestCase):
    def setUp(self):
        self.state = BorrowAccessState.independent(['value', 'other'])

    def test_owner_read_write(self):
        self.state.read('value')
        self.state.write('value')

    def test_multiple_shared_borrows(self):
        state = self.state.borrow('value', 'a').borrow('value', 'b')
        state.read('a')
        state.read('b')
        state.read('value')

    def test_shared_cannot_write(self):
        with self.assertRaises(OwnershipError):
            self.state.borrow('value', 'a').write('a')

    def test_owner_cannot_write_while_shared(self):
        with self.assertRaises(OwnershipError):
            self.state.borrow('value', 'a').write('value')

    def test_mutable_borrow_can_read_write(self):
        state = self.state.borrow('value', 'a', BorrowMode.MUTABLE)
        state.read('a')
        state.write('a')

    def test_mutable_blocks_owner_read(self):
        with self.assertRaises(OwnershipError):
            self.state.borrow('value', 'a', BorrowMode.MUTABLE).read('value')

    def test_mutable_blocks_owner_write(self):
        with self.assertRaises(OwnershipError):
            self.state.borrow('value', 'a', BorrowMode.MUTABLE).write('value')

    def test_mutable_blocks_shared(self):
        with self.assertRaises(OwnershipError):
            self.state.borrow('value', 'a', BorrowMode.MUTABLE).borrow('value', 'b')

    def test_shared_blocks_mutable(self):
        with self.assertRaises(OwnershipError):
            self.state.borrow('value', 'a').borrow('value', 'b', BorrowMode.MUTABLE)

    def test_two_mutable_conflict(self):
        with self.assertRaises(OwnershipError):
            self.state.borrow('value', 'a', BorrowMode.MUTABLE).borrow('value', 'b', BorrowMode.MUTABLE)

    def test_release_restores_owner_access(self):
        state = self.state.borrow('value', 'a', BorrowMode.MUTABLE).release('a')
        state.read('value')
        state.write('value')

    def test_independent_owners(self):
        state = self.state.borrow('value', 'a', BorrowMode.MUTABLE)
        state.write('other')
        state.borrow('other', 'b', BorrowMode.MUTABLE).write('b')

    def test_move_during_borrow_fails(self):
        with self.assertRaises(OwnershipError):
            self.state.borrow('value', 'a').move('value', 'new')

    def test_drop_during_borrow_fails(self):
        with self.assertRaises(OwnershipError):
            self.state.borrow('value', 'a').drop('value')

    def test_move_after_release(self):
        state = self.state.borrow('value', 'a').release('a').move('value', 'new')
        state.write('new')
        with self.assertRaises(OwnershipError):
            state.read('value')

    def test_snapshot_unchanged(self):
        self.state.borrow('value', 'a')
        self.state.write('value')

    def test_invalid_mode(self):
        with self.assertRaises(OwnershipError):
            self.state.borrow('value', 'a', 'mutable')

    def test_missing_reference_release(self):
        with self.assertRaises(OwnershipError):
            self.state.release('missing')


if __name__ == '__main__':
    unittest.main()
