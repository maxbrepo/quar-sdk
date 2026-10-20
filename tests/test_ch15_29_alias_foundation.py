"""Chapter 15.29: conservative may-alias foundation."""
import unittest
from frontend.quar.ast_nodes import FunctionCall
from qrvm.alias_analysis import AliasState
from qrvm.function_effects import FunctionEffects, call_invalidations


class AliasFoundationTests(unittest.TestCase):
    def setUp(self):
        self.base = AliasState.independent({'x', 'y', 'z'})

    def test_independent(self):
        self.assertFalse(self.base.may_alias('x', 'y'))

    def test_copy_alias(self):
        self.assertTrue(self.base.copy_alias('y', 'x').may_alias('x', 'y'))

    def test_copy_does_not_modify_original(self):
        self.base.copy_alias('y', 'x')
        self.assertFalse(self.base.may_alias('x', 'y'))

    def test_rebind_fresh(self):
        state = self.base.copy_alias('y', 'x').fresh('y', 'new_y')
        self.assertFalse(state.may_alias('x', 'y'))

    def test_unknown_escape(self):
        state = self.base.escape('x')
        self.assertEqual(state.affected({'x'}), frozenset({'x', 'y', 'z'}))

    def test_join_unions_possible_targets(self):
        joined = self.base.join(self.base.copy_alias('y', 'x'))
        self.assertTrue(joined.may_alias('x', 'y'))

    def test_join_requires_same_names(self):
        with self.assertRaises(ValueError):
            self.base.join(AliasState.independent({'x'}))

    def test_affected_alias_closure(self):
        self.assertEqual(self.base.copy_alias('y', 'x').affected({'x'}), frozenset({'x', 'y'}))

    def test_effects_expand_through_aliases(self):
        state = self.base.copy_alias('y', 'x')
        result = call_invalidations(FunctionCall('write', []), {'x', 'y', 'z'},
                                    {'write': FunctionEffects({'x'})}, state)
        self.assertEqual(result, frozenset({'x', 'y'}))

    def test_effects_without_alias_model_preserve_behavior(self):
        result = call_invalidations(FunctionCall('write', []), {'x', 'y'},
                                    {'write': FunctionEffects({'x'})})
        self.assertEqual(result, frozenset({'x'}))

    def test_unknown_call_remains_conservative(self):
        result = call_invalidations(FunctionCall('external', []), {'x', 'y', 'z'}, {}, self.base)
        self.assertEqual(result, frozenset({'x', 'y', 'z'}))

    def test_invalid_names(self):
        with self.assertRaises(KeyError):
            self.base.copy_alias('missing', 'x')


if __name__ == '__main__':
    unittest.main()
