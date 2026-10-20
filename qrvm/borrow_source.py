"""Opt-in source-to-scoped-CFG borrow analysis for a restricted Quar subset.

This is a diagnostic prototype, not a compiler or runtime safety gate.
"""
from dataclasses import dataclass
from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from qrvm.borrow_scoped_cfg import analyze_scoped_cfg
from qrvm.borrow_returns import summarize_function_returns
from qrvm.borrow_effects import summarize_function_effect
from frontend.quar import ast_nodes as ast
from qrvm.borrow_errors import UnsupportedBorrowError


@dataclass(frozen=True)
class SourceBorrowResult:
    statements: tuple
    scoped: object


def analyze_borrow_source(source: str, *, max_facts: int = 1024, pure_calls=(), infer_local_calls: bool = False) -> SourceBorrowResult:
    """Parse real Quar text, then check the supported AST subset.

    Parsing failures and unsupported AST constructs propagate as errors.
    This API never changes the semantics of ordinary Quar execution.
    """
    if not isinstance(source, str):
        raise TypeError('Quar source must be a string')
    statements = tuple(Parser(Lexer(source).tokenize()).parse())
    if not infer_local_calls:
        return SourceBorrowResult(statements, analyze_scoped_cfg(statements, max_facts=max_facts, pure_calls=pure_calls))
    if not isinstance(infer_local_calls, bool):
        raise TypeError('infer_local_calls must be bool')
    functions = [item for item in statements if isinstance(item, ast.FunctionDefinition)]
    names = [item.name for item in functions]
    if len(set(names)) != len(names):
        raise UnsupportedBorrowError('Duplicate function definitions cannot be inferred')
    certified = {item.name: item for item in functions if summarize_function_effect(item).classification == 'LOCAL_READ_ONLY' and summarize_function_returns(item).classification == 'SCALAR_VALUE'}
    trusted = set(pure_calls) | set(certified)
    # Verify every inferred call site, including arity. Unknown calls fail closed
    # in _reads; named arguments and defaults are not modeled for inference.
    def validate(expr):
        if isinstance(expr, ast.FunctionCall):
            if expr.name in certified:
                definition = certified[expr.name]
                if len(expr.arguments) != len(definition.parameters) or any(isinstance(a, ast.NamedArgument) for a in expr.arguments):
                    raise UnsupportedBorrowError(f'Unsupported inferred call signature: {expr.name}')
            for arg in expr.arguments:
                validate(arg.value if isinstance(arg, ast.NamedArgument) else arg)
        elif isinstance(expr, ast.BinaryOperation):
            validate(expr.left); validate(expr.right)
        elif isinstance(expr, ast.UnaryOperation):
            validate(expr.operand)
    def visit(body):
        for item in body:
            if isinstance(item, (ast.VariableDeclaration, ast.ConstantDeclaration, ast.Assignment)):
                validate(item.value)
            elif isinstance(item, ast.IfStatement):
                validate(item.condition); visit(item.then_body); visit(item.else_body)
            elif isinstance(item, ast.WhileStatement):
                validate(item.condition); visit(item.body)
    executable = tuple(item for item in statements if not isinstance(item, ast.FunctionDefinition))
    visit(executable)
    return SourceBorrowResult(statements, analyze_scoped_cfg(executable, max_facts=max_facts, pure_calls=trusted))


def analyze_borrow_file(path, *, encoding: str = 'utf-8', max_facts: int = 1024, pure_calls=(), infer_local_calls: bool = False):
    """Analyze a .vq file without executing it; return SourceBorrowResult."""
    from pathlib import Path
    return analyze_borrow_source(Path(path).read_text(encoding=encoding), max_facts=max_facts, pure_calls=pure_calls, infer_local_calls=infer_local_calls)
