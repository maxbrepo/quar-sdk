"""Chapter 15.26: fixed-array bounds and conservative call effects."""
import unittest

from frontend.quar.ast_nodes import (
    Assignment, BinaryOperation, FunctionCall, IfStatement, Integer, Variable,
)
from frontend.quar.errors import SemanticError
from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from frontend.quar.semantic import SemanticAnalyzer
from qrvm.control_flow import ControlFlowBuilder
from qrvm.optional_dataflow import OptionalDataflowAnalyzer
from qrvm.optional_flow import FlowState, Presence


class BoundsAndEffectsTests(unittest.TestCase):
    def check(self, source):
        SemanticAnalyzer().analyze(Parser(Lexer(source).tokenize()).parse())

    def state_at_exit(self, statements):
        graph = ControlFlowBuilder().build(statements)
        result = OptionalDataflowAnalyzer().analyze(
            graph, FlowState().set('x', Presence.PRESENT), ('x',)
        )
        return result.before(graph.exit).get('x')

    def test_constant_read_bound_rejected(self):
        with self.assertRaisesRegex(SemanticError, 'dimension 1'):
            self.check('i32 a[2] = {10, 20}; print(a[2]);')

    def test_constant_write_bound_rejected(self):
        with self.assertRaisesRegex(SemanticError, 'out of bounds'):
            self.check('i32 a[2] = {10, 20}; a[-1] = 3;')

    def test_variable_index_still_allowed(self):
        self.check('i32 a[2] = {10, 20}; i32 i = 1; print(a[i]);')

    def test_call_in_assignment_invalidates_other_fact(self):
        self.assertEqual(self.state_at_exit([Assignment('y', FunctionCall('change', []))]), Presence.UNKNOWN)

    def test_call_in_condition_invalidates_fact(self):
        self.assertEqual(self.state_at_exit([IfStatement(FunctionCall('change', []), [], [])]), Presence.UNKNOWN)

    def test_nested_call_in_condition_invalidates_fact(self):
        cond = BinaryOperation(Integer(1), '==', FunctionCall('change', []))
        self.assertEqual(self.state_at_exit([IfStatement(cond, [], [])]), Presence.UNKNOWN)

    def test_pure_presence_check_preserves_fact(self):
        cond = FunctionCall('present', [Variable('x')])
        self.assertEqual(self.state_at_exit([IfStatement(cond, [], [])]), Presence.UNKNOWN)
        # False edge proves absence; true edge proves presence, so join is unknown.

    def test_assignment_after_call_establishes_new_fact(self):
        self.assertEqual(self.state_at_exit([
            Assignment('y', FunctionCall('change', [])), Assignment('x', Integer(3))
        ]), Presence.PRESENT)


if __name__ == '__main__':
    unittest.main()
