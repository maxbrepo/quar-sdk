"""Chapter 15.33: integration regression tests."""
import unittest
from qrvm.borrow_lifetime import BorrowLifetimeState
from qrvm.borrow_access import BorrowMode
from qrvm.ownership_analysis import OwnershipError


class BorrowLifetimeTests(unittest.TestCase):
    def setUp(self):
        self.s = BorrowLifetimeState.empty().declare('value')

    def test_shared_read(self):
        s = self.s.borrow('value', 'r')
        s.read('r')
        s.read('value')

    def test_two_shared_reads(self):
        s = self.s.borrow('value', 'r1').borrow('value', 'r2')
        s.read('r1')
        s.read('r2')

    def test_shared_cannot_write(self):
        with self.assertRaises(OwnershipError):
            self.s.borrow('value', 'r').write('r')

    def test_shared_blocks_owner_write(self):
        with self.assertRaises(OwnershipError):
            self.s.borrow('value', 'r').write('value')

    def test_mutable_can_write(self):
        self.s.borrow('value', 'r', BorrowMode.MUTABLE).write('r')

    def test_mutable_blocks_owner_read(self):
        with self.assertRaises(OwnershipError):
            self.s.borrow('value', 'r', BorrowMode.MUTABLE).read('value')

    def test_mutable_blocks_shared(self):
        with self.assertRaises(OwnershipError):
            self.s.borrow('value', 'r', BorrowMode.MUTABLE).borrow('value', 'other')

    def test_shared_blocks_mutable(self):
        with self.assertRaises(OwnershipError):
            self.s.borrow('value', 'r').borrow('value', 'other', BorrowMode.MUTABLE)

    def test_release_restores_access(self):
        s = self.s.borrow('value', 'r').release('r')
        s.write('value')

    def test_move_blocked_while_borrowed(self):
        with self.assertRaises(OwnershipError):
            self.s.borrow('value', 'r').move('value', 'next')

    def test_move_marks_old_binding_unavailable(self):
        s = self.s.move('value', 'next')
        s.read('next')
        with self.assertRaises(OwnershipError):
            s.read('value')

    def test_scope_expiration_releases_borrow(self):
        s = self.s.enter('inner').borrow('value', 'r').exit()
        s.write('value')
        self.assertEqual(s.modes, {})

    def test_inner_owner_and_reference_expire(self):
        s = self.s.enter('inner').declare('local').borrow('local', 'r').exit()
        with self.assertRaises(OwnershipError):
            s.read('local')

    def test_outer_reference_cannot_outlive_inner_owner(self):
        s = self.s.borrow('value', 'outer').enter('inner').declare('local')
        # Existing borrow API only introduces a fresh reference in current scope.
        with self.assertRaises(OwnershipError):
            s.borrow('local', 'outer')

    def test_drop_blocked_while_borrowed(self):
        with self.assertRaises(OwnershipError):
            self.s.borrow('value', 'r').drop('value')

    def test_drop_marks_unavailable(self):
        s = self.s.drop('value')
        with self.assertRaises(OwnershipError):
            s.read('value')

    def test_immutable_snapshot(self):
        earlier = self.s
        later = earlier.borrow('value', 'r')
        self.assertEqual(earlier.modes, {})
        self.assertIn('r', later.modes)

    def test_root_scope_cannot_exit(self):
        with self.assertRaises(OwnershipError):
            self.s.exit()


if __name__ == '__main__':
    unittest.main()
