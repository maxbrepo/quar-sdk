"""Chapter 15.25: optional facts propagated through the CFG."""
import unittest

from frontend.quar.ast_nodes import (
    Assignment, Boolean, FunctionCall, IfStatement, Integer, LoopStatement,
    ReturnStatement, Variable, WhileStatement,
)
from qrvm.control_flow import ControlFlowBuilder
from qrvm.optional_dataflow import OptionalDataflowAnalyzer
from qrvm.optional_flow import FlowState, Presence


class OptionalCFGDataflowTests(unittest.TestCase):
    def analyze(self, statements, initial=None):
        graph = ControlFlowBuilder().build(statements)
        result = OptionalDataflowAnalyzer().analyze(graph, initial, ('x',))
        return graph, result

    def test_empty_graph(self):
        graph, result = self.analyze([])
        self.assertEqual(result.before(graph.exit).get('x'), Presence.UNKNOWN)

    def test_assignment_propagates(self):
        graph, result = self.analyze([Assignment('x', Integer(7))])
        self.assertEqual(result.before(graph.exit).get('x'), Presence.PRESENT)

    def test_absent_assignment_propagates(self):
        graph, result = self.analyze([Assignment('x', None)])
        self.assertEqual(result.before(graph.exit).get('x'), Presence.ABSENT)

    def test_copy_preserves_known_state(self):
        graph, result = self.analyze([Assignment('x', Variable('x'))], FlowState().set('x', Presence.ABSENT))
        self.assertEqual(result.before(graph.exit).get('x'), Presence.ABSENT)

    def test_branch_join_drops_conflicting_facts(self):
        graph, result = self.analyze([IfStatement(Boolean(True), [Assignment('x', Integer(1))], [Assignment('x', None)])])
        self.assertEqual(result.before(graph.exit).get('x'), Presence.UNKNOWN)

    def test_branch_join_preserves_agreement(self):
        graph, result = self.analyze([IfStatement(Boolean(True), [Assignment('x', None)], [Assignment('x', None)])])
        self.assertEqual(result.before(graph.exit).get('x'), Presence.ABSENT)

    def test_presence_guard_refines_true_edge(self):
        condition = FunctionCall('present', [Variable('x')])
        graph, result = self.analyze([IfStatement(condition, [ReturnStatement(Integer(1))], [])])
        return_node = next(n for n in graph.nodes if n.kind == 'return')
        self.assertEqual(result.before(return_node.id).get('x'), Presence.PRESENT)

    def test_presence_guard_refines_false_edge(self):
        condition = FunctionCall('present', [Variable('x')])
        graph, result = self.analyze([IfStatement(condition, [], [ReturnStatement(Integer(0))])])
        return_node = next(n for n in graph.nodes if n.kind == 'return')
        self.assertEqual(result.before(return_node.id).get('x'), Presence.ABSENT)

    def test_loop_converges_and_forgets_changed_fact(self):
        graph, result = self.analyze([WhileStatement(Boolean(True), [Assignment('x', None)])], FlowState().set('x', Presence.PRESENT))
        self.assertEqual(result.before(graph.exit).get('x'), Presence.UNKNOWN)

    def test_loop_without_writes_keeps_fact(self):
        graph, result = self.analyze([WhileStatement(Boolean(True), [])], FlowState().set('x', Presence.PRESENT))
        self.assertEqual(result.before(graph.exit).get('x'), Presence.PRESENT)

    def test_unreachable_after_return_has_no_state(self):
        graph, result = self.analyze([ReturnStatement(Integer(1)), Assignment('x', None)])
        unreachable = next(n for n in graph.nodes if n.kind == 'statement')
        self.assertIsNone(result.before(unreachable.id))

    def test_unknown_call_result_does_not_claim_presence(self):
        graph, result = self.analyze([Assignment('x', FunctionCall('unknown', []))])
        self.assertEqual(result.before(graph.exit).get('x'), Presence.UNKNOWN)

    def test_loop_break_terminates(self):
        from frontend.quar.ast_nodes import BreakStatement
        graph, result = self.analyze([LoopStatement([Assignment('x', None), BreakStatement()])])
        self.assertEqual(result.before(graph.exit).get('x'), Presence.ABSENT)


if __name__ == '__main__':
    unittest.main()
