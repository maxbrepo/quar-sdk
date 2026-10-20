"""Regression tests for the experimental Chapter 15.12 condition flow."""
import unittest

from frontend.quar.ast_nodes import Assignment, FunctionCall, Variable, VariableDeclaration
from memory.optional_condition_flow import merge_branches, split_presence
from memory.optional_frontend import OptionalFlowAnalyzer
from memory.optional_types import OptionalTypeError, Presence, ValueType


class PresenceConditionTests(unittest.TestCase):
    def setUp(self):
        self.flow = OptionalFlowAnalyzer()
        self.flow.declare(VariableDeclaration('int', 'item', None), optional=True)
        self.check = FunctionCall('present', [Variable('item')])

    def test_then_branch_is_readable(self):
        branches = split_presence(self.check, self.flow)
        self.assertEqual(branches.when_true.read(Variable('item')), ValueType('int'))

    def test_else_branch_is_not_readable(self):
        branches = split_presence(self.check, self.flow)
        with self.assertRaises(OptionalTypeError):
            branches.when_false.read(Variable('item'))

    def test_original_flow_unchanged(self):
        split_presence(self.check, self.flow)
        self.assertEqual(self.flow.values['item'].presence, Presence.UNKNOWN)

    def test_merge_discards_one_sided_presence(self):
        branches = split_presence(self.check, self.flow)
        merged = merge_branches(branches)
        self.assertEqual(merged.values['item'].presence, Presence.UNKNOWN)

    def test_assignment_invalidates_presence(self):
        branches = split_presence(self.check, self.flow)
        branches.when_true.assign(Assignment('item', Variable('other')), ValueType('int', True))
        with self.assertRaises(OptionalTypeError):
            branches.when_true.read(Variable('item'))

    def test_nonoptional_rejected(self):
        self.flow.declare(VariableDeclaration('int', 'count', None))
        with self.assertRaises(OptionalTypeError):
            split_presence(FunctionCall('present', [Variable('count')]), self.flow)

    def test_unknown_variable_rejected(self):
        with self.assertRaises(OptionalTypeError):
            split_presence(FunctionCall('present', [Variable('missing')]), self.flow)

    def test_unrecognized_condition_rejected(self):
        with self.assertRaises(OptionalTypeError):
            split_presence(Variable('item'), self.flow)


if __name__ == '__main__':
    unittest.main()
