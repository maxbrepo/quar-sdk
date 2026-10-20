"""Chapter 15.35: finite-state loop closure and fail-closed behavior."""
import unittest
from qrvm.borrow_flow import BorrowFlow
from qrvm.borrow_fixpoint import loop_fixpoint, state_key
from qrvm.ownership_analysis import OwnershipError


class BorrowFixpointTests(unittest.TestCase):
    def setUp(self):
        self.flow = BorrowFlow.empty().declare('value')

    def test_noop_converges(self):
        result = loop_fixpoint(self.flow, lambda flow: flow)
        self.assertEqual(result.reachable_states, 1)
        self.assertEqual(result.iterations, 1)

    def test_zero_iteration_path_is_retained(self):
        result = loop_fixpoint(self.flow, lambda flow: flow if 'ref' in flow.paths[0].modes else flow.borrow('value', 'ref'))
        self.assertEqual(result.reachable_states, 2)
        with self.assertRaises(OwnershipError):
            result.flow.write('value')

    def test_release_in_next_iteration(self):
        def body(flow):
            if 'ref' in flow.paths[0].modes:
                return flow.release('ref')
            return flow.borrow('value', 'ref')
        result = loop_fixpoint(self.flow, body)
        self.assertEqual(result.reachable_states, 2)
        self.assertEqual(result.iterations, 2)

    def test_branching_loop(self):
        result = loop_fixpoint(self.flow, lambda f: f.branch(lambda x: x, lambda x: x.borrow('value', 'ref')
                                  if 'ref' not in x.paths[0].modes else x))
        self.assertEqual(result.reachable_states, 2)

    def test_reject_write_on_any_reachable_path(self):
        result = loop_fixpoint(self.flow, lambda f: f if 'ref' in f.paths[0].modes else f.borrow('value', 'ref'))
        with self.assertRaisesRegex(OwnershipError, 'Owner write'):
            result.flow.write('value')

    def test_releasing_unknown_reference_fails(self):
        with self.assertRaises(OwnershipError):
            loop_fixpoint(self.flow, lambda f: f.release('ref'))

    def test_invalid_body_result(self):
        with self.assertRaises(OwnershipError):
            loop_fixpoint(self.flow, lambda f: None)

    def test_scope_leak_rejected(self):
        with self.assertRaises(OwnershipError):
            loop_fixpoint(self.flow, lambda f: f.enter('inner'))

    def test_unbounded_binding_growth_fails_closed(self):
        counter = iter(range(100))
        with self.assertRaisesRegex(OwnershipError, 'budget'):
            loop_fixpoint(self.flow, lambda f: f.declare('v' + str(next(counter))), max_states=4)

    def test_state_budget_rejects_zero(self):
        with self.assertRaises(OwnershipError):
            loop_fixpoint(self.flow, lambda f: f, max_states=0)

    def test_state_budget_rejects_bool(self):
        with self.assertRaises(OwnershipError):
            loop_fixpoint(self.flow, lambda f: f, max_states=True)

    def test_small_budget_convergent(self):
        result = loop_fixpoint(self.flow, lambda f: f, max_states=1)
        self.assertEqual(result.reachable_states, 1)

    def test_small_budget_nonconvergent(self):
        with self.assertRaises(OwnershipError):
            loop_fixpoint(self.flow, lambda f: f.borrow('value', 'ref'), max_states=1)

    def test_state_key_stable(self):
        self.assertEqual(state_key(self.flow.paths[0]), state_key(self.flow.paths[0]))

    def test_move_path_restricts_access(self):
        result = loop_fixpoint(self.flow, lambda f: f if 'next' in f.paths[0].lifetime.declared else f.move('value', 'next'))
        with self.assertRaises(OwnershipError):
            result.flow.read('value')


if __name__ == '__main__':
    unittest.main()
