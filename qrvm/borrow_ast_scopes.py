"""Lexically scoped AST borrow analysis for a deliberately restricted subset.

This is a standalone prototype; it does not change the Visual Quar compiler.
Branches are conservatively both reachable; loops use a finite-state closure.
"""
from dataclasses import dataclass
from frontend.quar import ast_nodes as ast
from qrvm.borrow_ast import _reads
from qrvm.borrow_flow import BorrowFlow
from qrvm.borrow_fixpoint import loop_fixpoint
from qrvm.ownership_analysis import OwnershipError
from qrvm.borrow_errors import UnsupportedBorrowError


@dataclass(frozen=True)
class ScopedASTResult:
    flow: BorrowFlow
    loop_applications: int


def analyze_scoped_ast(statements, initial=None, max_states=256):
    """Analyze declarations, assignments, if and while with lexical scopes.

    Declarations cannot shadow existing bindings in this initial model.
    Break, continue, return and unsupported syntax fail closed.
    """
    if isinstance(max_states, bool) or not isinstance(max_states, int) or max_states < 1:
        raise OwnershipError('State budget must be a positive integer')
    flow = BorrowFlow.empty() if initial is None else initial
    if not isinstance(flow, BorrowFlow):
        raise OwnershipError('Initial flow must be a BorrowFlow')
    counter = [0]

    def read_expr(expr, current):
        for name in _reads(expr):
            current.read(name)

    def scoped(body, current, label):
        entered = current.enter(label)
        return sequence(body, entered).exit()

    def sequence(body, current):
        for statement in body:
            if isinstance(statement, (ast.VariableDeclaration, ast.ConstantDeclaration)):
                read_expr(statement.value, current)
                current = current.declare(statement.name)
            elif isinstance(statement, ast.Assignment):
                read_expr(statement.value, current)
                current.write(statement.name)
            elif isinstance(statement, ast.IfStatement):
                read_expr(statement.condition, current)
                label_then = f'if_then_{id(statement)}'
                label_else = f'if_else_{id(statement)}'
                current = current.branch(
                    lambda f: scoped(statement.then_body, f, label_then),
                    lambda f: scoped(statement.else_body, f, label_else))
            elif isinstance(statement, ast.WhileStatement):
                label = f'while_{id(statement)}'

                def iteration(f):
                    read_expr(statement.condition, f)
                    return scoped(statement.body, f, label)

                result = loop_fixpoint(current, iteration, max_states=max_states)
                counter[0] += result.iterations
                current = result.flow
                read_expr(statement.condition, current)
            else:
                raise UnsupportedBorrowError(f'Unsupported scoped AST statement: {type(statement).__name__}')
        return current

    return ScopedASTResult(sequence(statements, flow), counter[0])
