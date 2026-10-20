"""Chapter 15.24: control-flow graph structural regression tests."""
import unittest
from frontend.quar.ast_nodes import (
    Assignment, Boolean, BreakStatement, ContinueStatement, DoWhileStatement,
    IfStatement, Integer, LoopStatement, ReturnStatement, WhileStatement,
)
from qrvm.control_flow import ControlFlowBuilder


class CFGTests(unittest.TestCase):
    def setUp(self):
        self.builder = ControlFlowBuilder()

    def test_empty_program(self):
        graph = self.builder.build([])
        self.assertEqual(graph.successors(graph.entry), (graph.exit,))

    def test_sequential_statements(self):
        graph = self.builder.build([Assignment('x', Integer(1)), Assignment('x', Integer(2))])
        self.assertEqual(len(graph.nodes), 4)
        self.assertEqual(len(graph.edges), 3)

    def test_if_has_true_false_edges(self):
        graph = self.builder.build([IfStatement(Boolean(True), [Assignment('x', Integer(1))], [])])
        branch = next(n for n in graph.nodes if n.kind == 'branch')
        self.assertEqual({e.label for e in graph.edges if e.source == branch.id}, {'true', 'false'})

    def test_while_has_back_edge(self):
        graph = self.builder.build([WhileStatement(Boolean(True), [Assignment('x', Integer(1))])])
        condition = next(n for n in graph.nodes if n.kind == 'condition')
        self.assertTrue(any(graph.nodes[p].kind == 'statement' for p in graph.predecessors(condition.id)))
        self.assertEqual(len(graph.successors(condition.id)), 2)

    def test_do_while_enters_body_first(self):
        graph = self.builder.build([DoWhileStatement([Assignment('x', Integer(1))], Boolean(True))])
        first = graph.successors(graph.entry)[0]
        self.assertEqual(graph.nodes[first].kind, 'statement')

    def test_break_exits_loop(self):
        graph = self.builder.build([LoopStatement([BreakStatement()])])
        node = next(n for n in graph.nodes if n.kind == 'break')
        self.assertEqual(graph.successors(node.id), (graph.exit,))

    def test_continue_returns_to_header(self):
        graph = self.builder.build([WhileStatement(Boolean(True), [ContinueStatement()])])
        node = next(n for n in graph.nodes if n.kind == 'continue')
        header = next(n for n in graph.nodes if n.kind == 'condition')
        self.assertEqual(graph.successors(node.id), (header.id,))

    def test_return_bypasses_following_statement(self):
        graph = self.builder.build([ReturnStatement(Integer(1)), Assignment('x', Integer(2))])
        node = next(n for n in graph.nodes if n.kind == 'return')
        self.assertEqual(graph.successors(node.id), (graph.exit,))

    def test_repeated_build_resets_state(self):
        first = self.builder.build([])
        second = self.builder.build([])
        self.assertEqual(first, second)

    def test_break_outside_loop_rejected(self):
        with self.assertRaises(ValueError):
            self.builder.build([BreakStatement()])


if __name__ == '__main__':
    unittest.main()
