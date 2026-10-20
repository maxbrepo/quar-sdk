"""Lexically scoped CFG borrow analysis for a restricted Visual Quar AST.

The CFG owns both control flow and lexical scope transitions. This prototype
intentionally does not infer source-language move or borrow semantics.
"""
from dataclasses import dataclass
from frontend.quar import ast_nodes as ast
from qrvm.borrow_ast import _reads
from qrvm.borrow_cfg import analyze_borrow_cfg
from qrvm.borrow_flow import BorrowFlow
from qrvm.control_flow import ControlFlowGraph, FlowNode, FlowEdge
from qrvm.ownership_analysis import OwnershipError
from qrvm.borrow_errors import UnsupportedBorrowError


@dataclass(frozen=True)
class ScopedCFGResult:
    graph: ControlFlowGraph
    analysis: object


def analyze_scoped_cfg(statements, initial=None, max_facts=1024, *, pure_calls=()):
    """Analyze if/else/while with lexical scope entry/exit on CFG edges.

    All branches are considered feasible. Unsupported constructs fail closed.
    Shadowing is not supported by the current lifetime model.
    """
    if isinstance(pure_calls, str) or any(not isinstance(name, str) or not name for name in pure_calls):
        raise ValueError('pure_calls must contain nonempty function names')
    pure_calls = frozenset(pure_calls)
    nodes = []
    edges = []

    def node(kind, statement=None):
        index = len(nodes)
        nodes.append(FlowNode(index, kind, statement))
        return index

    def edge(source, target, label='next'):
        edges.append(FlowEdge(source, target, label))

    entry = node('entry')
    exit_id = node('exit')

    def sequence(body, successor):
        current = successor
        for statement in reversed(body):
            if isinstance(statement, (ast.VariableDeclaration, ast.ConstantDeclaration, ast.Assignment)):
                index = node('statement', statement)
                edge(index, current)
                current = index
            elif isinstance(statement, ast.IfStatement):
                branch = node('branch', statement.condition)
                for label, branch_body in (('then', statement.then_body), ('else', statement.else_body)):
                    scope = f'if_{branch}_{label}'
                    leave = node('scope_exit')
                    edge(leave, current)
                    body_start = sequence(branch_body, leave)
                    enter = node('scope_enter', scope)
                    edge(enter, body_start)
                    edge(branch, enter, label)
                current = branch
            elif isinstance(statement, ast.WhileStatement):
                header = node('condition', statement.condition)
                scope = f'while_{header}'
                leave = node('scope_exit')
                edge(leave, header, 'backedge')
                body_start = sequence(statement.body, leave)
                enter = node('scope_enter', scope)
                edge(enter, body_start)
                edge(header, enter, 'true')
                edge(header, current, 'false')
                current = header
            else:
                raise UnsupportedBorrowError(f'Unsupported scoped CFG statement: {type(statement).__name__}')
        return current

    start = sequence(statements, exit_id)
    edge(entry, start)
    graph = ControlFlowGraph(tuple(nodes), tuple(edges), entry, exit_id)
    flow = BorrowFlow.empty() if initial is None else initial

    def transfer(current, state):
        if current.kind in ('entry', 'exit', 'scope_exit'):
            return state.exit() if current.kind == 'scope_exit' else state
        if current.kind == 'scope_enter':
            return state.enter(current.statement)
        if current.kind in ('branch', 'condition'):
            for name in _reads(current.statement, pure_calls):
                state.read(name)
            return state
        if current.kind == 'statement':
            stmt = current.statement
            for name in _reads(stmt.value, pure_calls):
                state.read(name)
            if isinstance(stmt, (ast.VariableDeclaration, ast.ConstantDeclaration)):
                return state.declare(stmt.name)
            state.write(stmt.name)
            return state
        raise UnsupportedBorrowError(f'Unsupported scoped CFG node: {current.kind}')

    return ScopedCFGResult(graph, analyze_borrow_cfg(graph, flow, transfer, max_facts=max_facts))
