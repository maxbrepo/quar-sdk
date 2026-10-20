"""Structured control-flow graph for future static analyses.

The graph is independent of QRVM bytecode and does not change code generation.
Unsupported compound statements remain opaque nodes (conservative boundary).
"""
from dataclasses import dataclass

from frontend.quar.ast_nodes import (
    BreakStatement, ContinueStatement, DoWhileStatement, ForStatement,
    IfStatement, LoopStatement, ReturnStatement, WhileStatement,
)


@dataclass(frozen=True)
class FlowNode:
    id: int
    kind: str
    statement: object = None


@dataclass(frozen=True)
class FlowEdge:
    source: int
    target: int
    label: str = "next"


@dataclass(frozen=True)
class ControlFlowGraph:
    nodes: tuple[FlowNode, ...]
    edges: tuple[FlowEdge, ...]
    entry: int
    exit: int

    def successors(self, node_id: int) -> tuple[int, ...]:
        return tuple(edge.target for edge in self.edges if edge.source == node_id)

    def predecessors(self, node_id: int) -> tuple[int, ...]:
        return tuple(edge.source for edge in self.edges if edge.target == node_id)


class ControlFlowBuilder:
    """Build a conservative CFG from a statement sequence."""

    def build(self, statements) -> ControlFlowGraph:
        self._nodes = []
        self._edges = []
        entry = self._node("entry")
        exit_id = self._node("exit")
        starts = self._sequence(statements, exit_id, None)
        self._edge(entry, starts)
        return ControlFlowGraph(tuple(self._nodes), tuple(self._edges), entry, exit_id)

    def _node(self, kind, statement=None):
        node_id = len(self._nodes)
        self._nodes.append(FlowNode(node_id, kind, statement))
        return node_id

    def _edge(self, source, target, label="next"):
        self._edges.append(FlowEdge(source, target, label))

    def _sequence(self, statements, successor, loop_targets):
        current = successor
        for statement in reversed(statements):
            current = self._statement(statement, current, loop_targets)
        return current

    def _statement(self, statement, successor, loop_targets):
        if isinstance(statement, ReturnStatement):
            node = self._node("return", statement)
            self._edge(node, 1, "return")
            return node
        if isinstance(statement, (BreakStatement, ContinueStatement)):
            if loop_targets is None:
                raise ValueError("break/continue outside a loop")
            node = self._node("break" if isinstance(statement, BreakStatement) else "continue", statement)
            self._edge(node, loop_targets[0] if isinstance(statement, BreakStatement) else loop_targets[1])
            return node
        if isinstance(statement, IfStatement):
            node = self._node("branch", statement.condition)
            then_start = self._sequence(statement.then_body, successor, loop_targets)
            else_start = self._sequence(statement.else_body, successor, loop_targets)
            self._edge(node, then_start, "true")
            self._edge(node, else_start, "false")
            return node
        if isinstance(statement, (WhileStatement, ForStatement, LoopStatement, DoWhileStatement)):
            is_do = isinstance(statement, DoWhileStatement)
            is_loop = isinstance(statement, LoopStatement)
            condition = None if is_loop else (statement.comparison if isinstance(statement, ForStatement) else statement.condition)
            header = self._node("loop" if is_loop else "condition", condition)
            body_start = self._sequence(statement.body, header, (successor, header))
            self._edge(header, body_start, "repeat" if is_loop else "true")
            if not is_loop:
                self._edge(header, successor, "false")
            return body_start if is_do else header
        node = self._node("statement", statement)
        self._edge(node, successor)
        return node
