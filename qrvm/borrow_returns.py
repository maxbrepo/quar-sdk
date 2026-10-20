"""Conservative return-origin classification for scalar Visual Quar functions.

This is not reference lifetime verification: unsupported types and expressions
remain UNKNOWN and must not be promoted to safe borrowed references.
"""
from dataclasses import dataclass
from frontend.quar import ast_nodes as ast
from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser

SCALARS = frozenset({'int', 'double', 'float', 'bool', 'char', 'string'})


@dataclass(frozen=True)
class ReturnSummary:
    name: str
    classification: str
    reason: str
    returns: int


def _value(expr, visible):
    if isinstance(expr, (ast.Integer, ast.Double, ast.Boolean, ast.String, ast.Char)):
        return
    if isinstance(expr, ast.Variable):
        if expr.name not in visible:
            raise ValueError(f'unbound return dependency: {expr.name}')
        return
    if isinstance(expr, ast.BinaryOperation):
        _value(expr.left, visible)
        _value(expr.right, visible)
        return
    if isinstance(expr, ast.UnaryOperation):
        _value(expr.operand, visible)
        return
    raise ValueError(f'unknown return expression: {type(expr).__name__}')


def _body(body, visible):
    count = 0
    guaranteed = False
    for statement in body:
        if guaranteed:
            break  # Unreachable statements cannot invalidate a proven return.
        if isinstance(statement, (ast.VariableDeclaration, ast.ConstantDeclaration)):
            if statement.var_type not in SCALARS or statement.name in visible:
                raise ValueError('non-scalar or shadowed local')
            _value(statement.value, visible)
            visible.add(statement.name)
        elif isinstance(statement, ast.Assignment):
            if statement.name not in visible:
                raise ValueError('assignment to unknown variable')
            _value(statement.value, visible)
        elif isinstance(statement, ast.ReturnStatement):
            if statement.value is None:
                raise ValueError('missing return value')
            _value(statement.value, visible)
            count += 1
            guaranteed = True
        elif isinstance(statement, ast.IfStatement):
            _value(statement.condition, visible)
            then_count, then_guaranteed = _body(statement.then_body, set(visible))
            else_count, else_guaranteed = _body(statement.else_body, set(visible))
            count += then_count + else_count
            guaranteed = guaranteed or (then_guaranteed and else_guaranteed)
        elif isinstance(statement, ast.WhileStatement):
            _value(statement.condition, visible)
            loop_count, _ = _body(statement.body, set(visible))
            count += loop_count
        else:
            raise ValueError(f'unknown return statement: {type(statement).__name__}')
    return count, guaranteed


def summarize_function_returns(function):
    if not isinstance(function, ast.FunctionDefinition):
        raise TypeError('Expected FunctionDefinition')
    try:
        if function.return_type not in SCALARS:
            raise ValueError('non-scalar return type')
        visible = set()
        for parameter in function.parameters:
            if parameter.var_type not in SCALARS or parameter.name in visible or parameter.default_value is not None:
                raise ValueError('unsupported parameter')
            visible.add(parameter.name)
        count, guaranteed = _body(function.body, visible)
        if count == 0:
            raise ValueError('no return statement')
        if not guaranteed:
            raise ValueError('not all execution paths return a value')
    except ValueError as exc:
        return ReturnSummary(function.name, 'UNKNOWN', str(exc), 0)
    return ReturnSummary(function.name, 'SCALAR_VALUE', 'Return expressions use only modeled scalar values', count)


def summarize_source_returns(source):
    statements = Parser(Lexer(source).tokenize()).parse()
    return tuple(summarize_function_returns(item) for item in statements if isinstance(item, ast.FunctionDefinition))
