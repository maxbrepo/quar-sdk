"""Tests of the experimental AST-to-optional-flow bridge."""
import unittest
from frontend.quar.ast_nodes import Assignment, Variable, VariableDeclaration
from memory.optional_types import OptionalTypeError, Presence, ValueType
from memory.optional_frontend import OptionalFlowAnalyzer


class OptionalFrontendTests(unittest.TestCase):
    def setUp(self):
        self.analyzer = OptionalFlowAnalyzer()
        self.analyzer.declare(VariableDeclaration('int', 'item', None), optional=True)

    def test_unchecked_optional_read_fails(self):
        with self.assertRaises(OptionalTypeError):
            self.analyzer.read(Variable('item'))

    def test_presence_check_enables_read(self):
        self.analyzer.refine_present('item')
        self.assertEqual(self.analyzer.read(Variable('item')), ValueType('int'))

    def test_assignment_invalidates_presence(self):
        self.analyzer.refine_present('item')
        self.analyzer.assign(Assignment('item', None), ValueType('int', True))
        with self.assertRaises(OptionalTypeError):
            self.analyzer.read(Variable('item'))

    def test_nonoptional_assignment_is_present(self):
        self.analyzer.assign(Assignment('item', None), ValueType('int'))
        self.assertEqual(self.analyzer.read(Variable('item')), ValueType('int'))

    def test_optional_to_nonoptional_rejected(self):
        self.analyzer.declare(VariableDeclaration('int', 'strict', None))
        with self.assertRaises(OptionalTypeError):
            self.analyzer.assign(Assignment('strict', None), ValueType('int', True))

    def test_branch_merge_forgets_one_sided_check(self):
        branch = self.analyzer.fork()
        branch.refine_present('item')
        self.analyzer.merge(branch)
        with self.assertRaises(OptionalTypeError):
            self.analyzer.read(Variable('item'))

    def test_branch_merge_preserves_both_sided_check(self):
        branch = self.analyzer.fork()
        self.analyzer.refine_present('item')
        branch.refine_present('item')
        self.analyzer.merge(branch)
        self.assertEqual(self.analyzer.read(Variable('item')), ValueType('int'))

    def test_known_absence_rejects_read(self):
        self.analyzer.refine_absent('item')
        with self.assertRaises(OptionalTypeError):
            self.analyzer.read(Variable('item'))


if __name__ == '__main__':
    unittest.main()
