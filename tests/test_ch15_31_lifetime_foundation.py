"""Chapter 15.31: lexical scope and reference lifetime model."""
import unittest
from qrvm.lifetime_analysis import LifetimeState
from qrvm.ownership_analysis import OwnershipError


class LifetimeFoundationTests(unittest.TestCase):
    def test_root_owner(self):
        LifetimeState.empty().declare('a').require_access('a')

    def test_scope_exit_expires_owner(self):
        state = LifetimeState.empty().enter('inner').declare('a').exit()
        with self.assertRaises(OwnershipError):
            state.require_access('a')

    def test_outer_owner_survives_inner(self):
        state = LifetimeState.empty().declare('a').enter('inner').exit()
        state.require_access('a')

    def test_inner_borrow_expires(self):
        state = LifetimeState.empty().declare('a').enter('inner').borrow('a', 'r').exit()
        state.require_access('a')
        with self.assertRaises(OwnershipError):
            state.require_access('r')

    def test_nested_scopes(self):
        state = LifetimeState.empty().declare('a').enter('first').enter('second').borrow('a', 'r')
        state = state.exit().exit()
        state.require_access('a')

    def test_inner_owner_cannot_be_borrowed_in_outer_scope(self):
        state = LifetimeState.empty().enter('inner').declare('a')
        with self.assertRaises(OwnershipError):
            LifetimeState(state.ownership.borrow('a', 'r'), state.scopes, {'a': 'inner', 'r': 'root'})

    def test_move_to_inner_scope(self):
        state = LifetimeState.empty().declare('a').enter('inner').move('a', 'b').exit()
        with self.assertRaises(OwnershipError):
            state.require_access('a')
        with self.assertRaises(OwnershipError):
            state.require_access('b')

    def test_duplicate_scope(self):
        with self.assertRaises(OwnershipError):
            LifetimeState.empty().enter('root')

    def test_root_cannot_exit(self):
        with self.assertRaises(OwnershipError):
            LifetimeState.empty().exit()

    def test_duplicate_binding(self):
        with self.assertRaises(OwnershipError):
            LifetimeState.empty().declare('a').declare('a')

    def test_borrow_blocks_move(self):
        state = LifetimeState.empty().declare('a').borrow('a', 'r')
        with self.assertRaises(OwnershipError):
            state.move('a', 'b')

    def test_release_then_move(self):
        state = LifetimeState.empty().declare('a').borrow('a', 'r').release('r').move('a', 'b')
        state.require_access('b')

    def test_original_unchanged(self):
        initial = LifetimeState.empty().declare('a')
        initial.enter('inner').declare('b')
        initial.require_access('a')
        self.assertEqual(initial.scopes, ('root',))


if __name__ == '__main__':
    unittest.main()
