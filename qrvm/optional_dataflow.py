"""Forward optional-presence analysis over a structured CFG.

This analysis is diagnostic infrastructure only: it does not alter QRVM bytecode.
Unknown facts are conservative; unreachable nodes have no input state.
"""
from collections import deque
from dataclasses import dataclass

from frontend.quar.ast_nodes import (
    Assignment, BinaryOperation, Boolean, ConstantDeclaration, FunctionCall, UnaryOperation,
    Variable, VariableDeclaration,
)
from .optional_flow import FlowState, Presence
from .function_effects import call_invalidations


@dataclass(frozen=True)
class DataflowResult:
    entry_states: dict[int, FlowState]
    exit_states: dict[int, FlowState]

    def before(self, node_id: int) -> FlowState | None:
        return self.entry_states.get(node_id)

    def after(self, node_id: int) -> FlowState | None:
        return self.exit_states.get(node_id)


def _has_opaque_call(expression):
    """Conservatively detect calls that may change previously established facts."""
    if expression is None:
        return False
    if isinstance(expression, FunctionCall):
        if expression.name != 'present' or len(expression.arguments) != 1:
            return True
        return any(_has_opaque_call(arg) for arg in expression.arguments)
    if isinstance(expression, BinaryOperation):
        return _has_opaque_call(expression.left) or _has_opaque_call(expression.right)
    if isinstance(expression, UnaryOperation):
        return _has_opaque_call(expression.operand)
    return False


def _condition_fact(expression, truth):
    """Return a single proven presence fact, if the condition supports one."""
    if isinstance(expression, UnaryOperation) and expression.operator in ('not', '!'):
        return _condition_fact(expression.operand, not truth)
    if isinstance(expression, FunctionCall) and expression.name == 'present' and len(expression.arguments) == 1:
        argument = expression.arguments[0]
        if isinstance(argument, Variable):
            return argument.name, Presence.PRESENT if truth else Presence.ABSENT
    return None


def _assigned_presence(value, state):
    if value is None:
        return Presence.ABSENT
    if isinstance(value, Variable):
        return state.get(value.name)
    if isinstance(value, FunctionCall):
        return Presence.UNKNOWN
    return Presence.PRESENT


class OptionalDataflowAnalyzer:
    """Compute guaranteed facts at each reachable CFG node until convergence."""

    def analyze(self, graph, initial_state=None, optional_names=(), function_effects=None):
        initial_state = initial_state if initial_state is not None else FlowState()
        optional_names = frozenset(optional_names)
        function_effects = {} if function_effects is None else dict(function_effects)
        nodes = {node.id: node for node in graph.nodes}
        edges = {}
        for edge in graph.edges:
            edges.setdefault(edge.source, []).append(edge)
        before = {graph.entry: initial_state}
        after = {}
        pending = deque([graph.entry])
        queued = {graph.entry}

        while pending:
            node_id = pending.popleft()
            queued.remove(node_id)
            node = nodes[node_id]
            state = before[node_id]
            output = self._transfer(node, state, optional_names, function_effects)
            if node.kind in ('branch', 'condition'):
                output = output.invalidate(call_invalidations(node.statement, optional_names, function_effects))
            after[node_id] = output
            for edge in edges.get(node_id, ()):
                propagated = output
                if node.kind in ('branch', 'condition') and edge.label in ('true', 'false'):
                    fact = _condition_fact(node.statement, edge.label == 'true')
                    if fact is not None and fact[0] in optional_names:
                        propagated = propagated.set(*fact)
                old = before.get(edge.target)
                combined = propagated if old is None else old.join(propagated)
                if old is None or combined != old:
                    before[edge.target] = combined
                    if edge.target not in queued:
                        pending.append(edge.target)
                        queued.add(edge.target)
        return DataflowResult(before, after)

    @staticmethod
    def _transfer(node, state, optional_names, function_effects):
        statement = node.statement
        if node.kind != 'statement':
            return state
        if isinstance(statement, (VariableDeclaration, ConstantDeclaration, Assignment)):
            state = state.invalidate(call_invalidations(statement.value, optional_names, function_effects))
            if statement.name in optional_names:
                return state.set(statement.name, _assigned_presence(statement.value, state))
        # Opaque statements may have effects; discard guarantees, not types.
        elif statement is not None:
            return state.invalidate(optional_names)
        return state
