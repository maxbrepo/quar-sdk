"""Chapter 15.30 ownership foundation tests."""
import unittest
from qrvm.ownership_analysis import OwnershipState, OwnershipError, OwnershipKind


class OwnershipFoundationTests(unittest.TestCase):
    def test_independent(self):
        state = OwnershipState.independent(['a', 'b'])
        state.require_access('a')
        self.assertEqual(state.owners['b'], OwnershipKind.OWNED)

    def test_duplicate(self):
        with self.assertRaises(OwnershipError):
            OwnershipState.independent(['a', 'a'])

    def test_move(self):
        state = OwnershipState.independent(['a']).move('a', 'b')
        state.require_access('b')
        with self.assertRaises(OwnershipError):
            state.require_access('a')

    def test_double_move(self):
        state = OwnershipState.independent(['a']).move('a', 'b')
        with self.assertRaises(OwnershipError):
            state.move('a', 'c')

    def test_borrow(self):
        state = OwnershipState.independent(['a']).borrow('a', 'ref')
        state.require_access('ref')
        state.require_access('a')

    def test_borrow_prevents_move(self):
        state = OwnershipState.independent(['a']).borrow('a', 'ref')
        with self.assertRaises(OwnershipError):
            state.move('a', 'b')

    def test_release_allows_move(self):
        state = OwnershipState.independent(['a']).borrow('a', 'ref').release('ref')
        state.move('a', 'b').require_access('b')

    def test_drop_prevents_access(self):
        state = OwnershipState.independent(['a']).drop('a')
        with self.assertRaises(OwnershipError):
            state.require_access('a')

    def test_drop_prevented_during_borrow(self):
        state = OwnershipState.independent(['a']).borrow('a', 'ref')
        with self.assertRaises(OwnershipError):
            state.drop('a')

    def test_cannot_borrow_moved(self):
        state = OwnershipState.independent(['a']).move('a', 'b')
        with self.assertRaises(OwnershipError):
            state.borrow('a', 'ref')

    def test_immutable_transition(self):
        original = OwnershipState.independent(['a'])
        original.move('a', 'b')
        original.require_access('a')

    def test_unknown_borrow(self):
        with self.assertRaises(OwnershipError):
            OwnershipState.independent(['a']).release('missing')


if __name__ == '__main__':
    unittest.main()
