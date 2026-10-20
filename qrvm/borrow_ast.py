"""Conservative AST-to-borrow-CFG adapter (read/write only).

No source-level move, borrow, or implicit ownership semantics are inferred.
Unsupported expressions/statements fail closed instead of being skipped.
"""
from dataclasses import dataclass
from frontend.quar import ast_nodes as ast
from qrvm.borrow_cfg import analyze_borrow_cfg
from qrvm.borrow_flow import BorrowFlow
from qrvm.control_flow import ControlFlowBuilder
from qrvm.ownership_analysis import OwnershipError
from qrvm.borrow_errors import UnsupportedBorrowError


@dataclass(frozen=True)
class ASTBorrowResult:
    graph: object
    analysis: object


def _reads(expr, pure_calls=frozenset()):
    if isinstance(expr, ast.Variable):
        return (expr.name,)
    if isinstance(expr, (ast.Integer, ast.Double, ast.Boolean, ast.String, ast.Char)):
        return ()
    if isinstance(expr, ast.BinaryOperation):
        return _reads(expr.left, pure_calls) + _reads(expr.right, pure_calls)
    if isinstance(expr, ast.UnaryOperation):
        return _reads(expr.operand, pure_calls)
    if isinstance(expr, ast.FunctionCall):
        if expr.name not in pure_calls:
            raise UnsupportedBorrowError(f'Unsupported function call effects: {expr.name}')
        reads = ()
        for argument in expr.arguments:
            if isinstance(argument, ast.NamedArgument):
                argument = argument.value
            reads += _reads(argument, pure_calls)
        return reads
    raise UnsupportedBorrowError(f'Unsupported expression for borrow AST analysis: {type(expr).__name__}')


def analyze_borrow_ast(statements, initial=None, max_facts=1024):
    """Check a conservative subset of AST with CFG branch/loop propagation.

    Each declaration creates an independent abstract owner; assignment reads
    its RHS and writes an existing owner. These are analysis assumptions only.
    """
    graph = ControlFlowBuilder().build(statements)
    initial = BorrowFlow.empty() if initial is None else initial

    def transfer(node, flow):
        stmt = node.statement
        if node.kind in ('entry', 'exit', 'break', 'continue'):
            return flow
        if node.kind in ('branch', 'condition'):
            for name in _reads(stmt):
                flow.read(name)
            return flow
        if node.kind == 'loop':
            return flow
        if node.kind == 'return':
            if stmt.value is not None:
                for name in _reads(stmt.value):
                    flow.read(name)
            return flow
        if node.kind != 'statement':
            raise UnsupportedBorrowError(f'Unsupported CFG node: {node.kind}')
        if isinstance(stmt, (ast.VariableDeclaration, ast.ConstantDeclaration)):
            for name in _reads(stmt.value):
                flow.read(name)
            return flow.declare(stmt.name)
        if isinstance(stmt, ast.Assignment):
            for name in _reads(stmt.value):
                flow.read(name)
            flow.write(stmt.name)
            return flow
        raise UnsupportedBorrowError(f'Unsupported statement for borrow AST analysis: {type(stmt).__name__}')

    return ASTBorrowResult(graph, analyze_borrow_cfg(graph, initial, transfer, max_facts=max_facts))
