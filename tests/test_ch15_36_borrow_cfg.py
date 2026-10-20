import unittest
from qrvm.control_flow import ControlFlowGraph, FlowNode, FlowEdge
from qrvm.borrow_flow import BorrowFlow
from qrvm.borrow_cfg import analyze_borrow_cfg
from qrvm.ownership_analysis import OwnershipError


def graph(edges, count=4):
    return ControlFlowGraph(tuple(FlowNode(i, 'statement') for i in range(count)),
                            tuple(FlowEdge(*edge) for edge in edges), 0, count - 1)


def initial():
    return BorrowFlow.empty().declare('value')


class CFGTests(unittest.TestCase):
    def test_linear(self):
        result = analyze_borrow_cfg(graph([(0, 1), (1, 2), (2, 3)]), initial(),
                                    lambda node, flow: flow)
        self.assertEqual(result.facts, 4)
        self.assertIsNotNone(result.at(3))

    def test_loop_converges(self):
        result = analyze_borrow_cfg(graph([(0, 1), (1, 2), (2, 1), (2, 3)]),
                                    initial(), lambda node, flow: flow)
        self.assertEqual(result.facts, 4)

    def test_branch_conflict(self):
        cfg = graph([(0, 1), (0, 2), (1, 3), (2, 3)])
        def transfer(node, flow):
            if node.id == 1:
                return flow.borrow('value', 'ref')
            if node.id == 3:
                flow.write('value')
            return flow
        with self.assertRaisesRegex(OwnershipError, 'conflict'):
            analyze_borrow_cfg(cfg, initial(), transfer)

    def test_release_restores_write(self):
        cfg = graph([(0, 1), (1, 2), (2, 3)])
        def transfer(node, flow):
            if node.id == 1:
                return flow.borrow('value', 'ref')
            if node.id == 2:
                return flow.release('ref')
            if node.id == 3:
                flow.write('value')
            return flow
        self.assertIsNotNone(analyze_borrow_cfg(cfg, initial(), transfer).at(3))

    def test_edge_filter(self):
        cfg = graph([(0, 1), (0, 2), (1, 3), (2, 3)])
        result = analyze_borrow_cfg(cfg, initial(), lambda node, flow: flow,
                                    lambda edge, state: edge.target != 2)
        self.assertIsNone(result.at(2))

    def test_budget_fails_closed(self):
        with self.assertRaisesRegex(OwnershipError, 'budget exceeded'):
            analyze_borrow_cfg(graph([(0, 1), (1, 2)]), initial(),
                               lambda node, flow: flow, max_facts=2)

    def test_invalid_transfer(self):
        with self.assertRaisesRegex(OwnershipError, 'must return'):
            analyze_borrow_cfg(graph([(0, 1)]), initial(), lambda node, flow: None)

    def test_invalid_graph(self):
        cfg = graph([(0, 5)])
        with self.assertRaisesRegex(OwnershipError, 'unknown node'):
            analyze_borrow_cfg(cfg, initial(), lambda node, flow: flow)

    def test_repeated_borrow_release_loop(self):
        cfg = graph([(0, 1), (1, 2), (2, 1), (2, 3)])
        def transfer(node, flow):
            if node.id == 1:
                return flow.borrow('value', 'ref')
            if node.id == 2:
                return flow.release('ref')
            if node.id == 3:
                flow.write('value')
            return flow
        result = analyze_borrow_cfg(cfg, initial(), transfer)
        self.assertEqual(result.facts, 4)

    def test_invalid_budget(self):
        with self.assertRaises(OwnershipError):
            analyze_borrow_cfg(graph([]), initial(), lambda node, flow: flow, max_facts=0)


if __name__ == '__main__':
    unittest.main()
