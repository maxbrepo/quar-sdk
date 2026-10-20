"""Experimental AST-level presence refinement; not wired into .vq semantics.

A FunctionCall named 'present' is used only as a test fixture here. The
language has not committed to this spelling or runtime implementation.
"""
from dataclasses import dataclass

from frontend.quar.ast_nodes import FunctionCall, Variable
from memory.optional_frontend import OptionalFlowAnalyzer
from memory.optional_types import OptionalTypeError


@dataclass(frozen=True)
class PresenceBranches:
    when_true: OptionalFlowAnalyzer
    when_false: OptionalFlowAnalyzer


def split_presence(condition: object, flow: OptionalFlowAnalyzer) -> PresenceBranches:
    """Fork and refine both paths of a recognized experimental presence test."""
    if not (isinstance(condition, FunctionCall)
            and condition.name == 'present'
            and len(condition.arguments) == 1
            and isinstance(condition.arguments[0], Variable)):
        raise OptionalTypeError('Unsupported presence condition')
    name = condition.arguments[0].name
    if name not in flow.values:
        raise OptionalTypeError(f'Unknown variable: {name}')
    if not flow.values[name].type.optional:
        raise OptionalTypeError(f'Presence test requires an optional: {name}')
    yes, no = flow.fork(), flow.fork()
    yes.refine_present(name)
    no.refine_absent(name)
    return PresenceBranches(yes, no)


def merge_branches(branches: PresenceBranches) -> OptionalFlowAnalyzer:
    """Join independent branches, discarding facts not true on both paths."""
    merged = branches.when_true.fork()
    merged.merge(branches.when_false)
    return merged
