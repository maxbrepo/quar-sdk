"""Conservative path-sensitive borrow propagation over an existing CFG.

Transfer functions are explicit analysis callbacks, not inferred source semantics.
A finite state budget is mandatory; unsupported transfers must fail closed.
"""
from dataclasses import dataclass
from collections import deque
from typing import Callable
from qrvm.control_flow import ControlFlowGraph, FlowNode, FlowEdge
from qrvm.borrow_flow import BorrowFlow
from qrvm.borrow_fixpoint import state_key
from qrvm.borrow_lifetime import BorrowLifetimeState
from qrvm.ownership_analysis import OwnershipError


@dataclass(frozen=True)
class CFGResult:
    states: dict[int, BorrowFlow]
    processed: int
    facts: int

    def at(self, node_id: int) -> BorrowFlow | None:
        return self.states.get(node_id)


def analyze_borrow_cfg(
    graph: ControlFlowGraph,
    initial: BorrowFlow,
    transfer: Callable[[FlowNode, BorrowFlow], BorrowFlow],
    edge_filter: Callable[[FlowEdge, BorrowLifetimeState], bool] | None = None,
    max_facts: int = 1024,
) -> CFGResult:
    """Propagate each reachable abstract state until all CFG backedges stabilize.

    Each state is checked by transfer; conflicts raise OwnershipError. Facts are
    deduplicated per node. An exhausted budget raises rather than succeeding.
    Edge filtering is optional; absent a filter, every edge is feasible.
    """
    if not isinstance(graph, ControlFlowGraph) or not isinstance(initial, BorrowFlow):
        raise OwnershipError('CFG and initial BorrowFlow are required')
    if not callable(transfer) or (edge_filter is not None and not callable(edge_filter)):
        raise OwnershipError('Invalid CFG transfer or edge filter')
    if isinstance(max_facts, bool) or not isinstance(max_facts, int) or max_facts < 1:
        raise OwnershipError('Fact budget must be a positive integer')
    nodes = {node.id: node for node in graph.nodes}
    if len(nodes) != len(graph.nodes) or graph.entry not in nodes or graph.exit not in nodes:
        raise OwnershipError('Invalid CFG nodes')
    outgoing = {node_id: [] for node_id in nodes}
    for edge in graph.edges:
        if edge.source not in nodes or edge.target not in nodes:
            raise OwnershipError('CFG edge refers to unknown node')
        outgoing[edge.source].append(edge)
    facts: dict[int, dict[tuple, BorrowLifetimeState]] = {node_id: {} for node_id in nodes}
    queue = deque()
    count = 0

    def add(node_id, state):
        nonlocal count
        key = state_key(state)
        if key in facts[node_id]:
            return
        if count >= max_facts:
            raise OwnershipError('CFG fact budget exceeded; convergence not proven')
        facts[node_id][key] = state
        count += 1
        queue.append((node_id, key))

    for state in initial.paths:
        add(graph.entry, state)
    processed = 0
    while queue:
        node_id, key = queue.popleft()
        state = facts[node_id][key]
        result = transfer(nodes[node_id], BorrowFlow((state,)))
        processed += 1
        if not isinstance(result, BorrowFlow):
            raise OwnershipError('CFG transfer must return BorrowFlow')
        for successor in result.paths:
            for edge in outgoing[node_id]:
                if edge_filter is None or edge_filter(edge, successor):
                    add(edge.target, successor)
    return CFGResult({node_id: BorrowFlow(tuple(paths.values()))
                      for node_id, paths in facts.items() if paths}, processed, count)
