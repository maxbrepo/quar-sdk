import unittest
from qrvm.borrow_flow import BorrowFlow
from qrvm.borrow_access import BorrowMode
from qrvm.ownership_analysis import OwnershipError


class BorrowFlowTests(unittest.TestCase):
    def setUp(self):
        self.flow = BorrowFlow.empty().declare('item')

    def test_initial(self):
        self.assertEqual(len(self.flow.paths), 1)

    def test_read(self):
        self.flow.read('item')

    def test_branch_paths(self):
        flow = self.flow.branch(lambda f: f, lambda f: f)
        self.assertEqual(len(flow.paths), 2)

    def test_shared_borrow_on_one_branch_blocks_owner_write(self):
        flow = self.flow.branch(lambda f: f.borrow('item', 'ref'), lambda f: f)
        with self.assertRaises(OwnershipError):
            flow.write('item')

    def test_shared_borrow_allows_read(self):
        flow = self.flow.branch(lambda f: f.borrow('item', 'ref'), lambda f: f)
        flow.read('item')

    def test_mutable_borrow_blocks_owner_read(self):
        flow = self.flow.branch(lambda f: f.borrow('item', 'ref', BorrowMode.MUTABLE), lambda f: f)
        with self.assertRaises(OwnershipError):
            flow.read('item')

    def test_branch_move_blocks_read(self):
        flow = self.flow.branch(lambda f: f.move('item', 'other'), lambda f: f)
        with self.assertRaises(OwnershipError):
            flow.read('item')

    def test_branch_drop_blocks_read(self):
        flow = self.flow.branch(lambda f: f.drop('item'), lambda f: f)
        with self.assertRaises(OwnershipError):
            flow.read('item')

    def test_identical_branches_allow_write(self):
        flow = self.flow.branch(lambda f: f, lambda f: f)
        flow.write('item')

    def test_branch_scope_mismatch_rejected(self):
        with self.assertRaises(OwnershipError):
            self.flow.branch(lambda f: f.enter('inner'), lambda f: f)

    def test_scope_release_after_branch(self):
        flow = self.flow.enter('inner').branch(
            lambda f: f.borrow('item', 'ref'), lambda f: f)
        flow = flow.exit()
        flow.write('item')

    def test_zero_or_one_loop_borrow(self):
        flow = self.flow.loop_once(lambda f: f.borrow('item', 'ref'))
        with self.assertRaises(OwnershipError):
            flow.write('item')

    def test_zero_or_one_loop_move(self):
        flow = self.flow.loop_once(lambda f: f.move('item', 'other'))
        with self.assertRaises(OwnershipError):
            flow.read('item')

    def test_invalid_operation_on_any_path_rejected(self):
        flow = self.flow.branch(lambda f: f.borrow('item', 'ref'), lambda f: f)
        with self.assertRaises(OwnershipError):
            flow.release('ref')

    def test_loop_body_invalid(self):
        with self.assertRaises(OwnershipError):
            self.flow.loop_once(lambda f: None)

    def test_branch_invalid(self):
        with self.assertRaises(OwnershipError):
            self.flow.branch(lambda f: None, lambda f: f)

    def test_empty_paths_rejected(self):
        with self.assertRaises(OwnershipError):
            BorrowFlow(())

    def test_explicit_mutable_write(self):
        flow = self.flow.borrow('item', 'ref', BorrowMode.MUTABLE)
        flow.write('ref')
        with self.assertRaises(OwnershipError):
            flow.write('item')
