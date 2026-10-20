"""Conservative local function-effect summaries for borrow analysis.

Only scalar, call-free, locally scoped bodies are certified. Certification
means 'no modeled external writes/calls', not full purity or memory safety.
"""
from dataclasses import dataclass
from frontend.quar import ast_nodes as ast
from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser


@dataclass(frozen=True)
class FunctionEffect:
    name: str
    classification: str
    reason: str


def _scalar(type_name):
    return type_name in {'int', 'double', 'float', 'bool', 'char', 'string'}


def _check_expression(expr, visible):
    if isinstance(expr, ast.Variable):
        if expr.name not in visible:
            raise ValueError(f'unbound read: {expr.name}')
    elif isinstance(expr, (ast.Integer, ast.Double, ast.Boolean, ast.String, ast.Char)):
        return
    elif isinstance(expr, ast.BinaryOperation):
        _check_expression(expr.left, visible)
        _check_expression(expr.right, visible)
    elif isinstance(expr, ast.UnaryOperation):
        _check_expression(expr.operand, visible)
    else:
        raise ValueError(f'unmodeled expression: {type(expr).__name__}')


def _check_body(body, visible, parameters):
    locals_here = set()
    for statement in body:
        if isinstance(statement, (ast.VariableDeclaration, ast.ConstantDeclaration)):
            if not _scalar(statement.var_type):
                raise ValueError('non-scalar local')
            _check_expression(statement.value, visible)
            if statement.name in visible:
                raise ValueError('shadowing or duplicate local')
            visible.add(statement.name)
            locals_here.add(statement.name)
        elif isinstance(statement, ast.Assignment):
            _check_expression(statement.value, visible)
            if statement.name not in visible or statement.name in parameters:
                raise ValueError('non-local or parameter write')
        elif isinstance(statement, ast.ReturnStatement):
            if statement.value is not None:
                _check_expression(statement.value, visible)
        elif isinstance(statement, ast.IfStatement):
            _check_expression(statement.condition, visible)
            _check_body(statement.then_body, set(visible), parameters)
            _check_body(statement.else_body, set(visible), parameters)
        elif isinstance(statement, ast.WhileStatement):
            _check_expression(statement.condition, visible)
            _check_body(statement.body, set(visible), parameters)
        else:
            raise ValueError(f'unmodeled statement: {type(statement).__name__}')
    visible.difference_update(locals_here)


def summarize_function_effect(function):
    """Classify one function, conservatively; never assume unknown calls pure."""
    if not isinstance(function, ast.FunctionDefinition):
        raise TypeError('Expected FunctionDefinition')
    try:
        if not _scalar(function.return_type) and function.return_type != 'void':
            raise ValueError('non-scalar return')
        names = set()
        for parameter in function.parameters:
            if not _scalar(parameter.var_type) or parameter.name in names or parameter.default_value is not None:
                raise ValueError('unsupported parameter')
            names.add(parameter.name)
        _check_body(function.body, set(names), names)
    except ValueError as exc:
        return FunctionEffect(function.name, 'UNKNOWN', str(exc))
    return FunctionEffect(function.name, 'LOCAL_READ_ONLY', 'No modeled external writes or calls')


def summarize_source_effects(source):
    """Parse source and report definitions; does not alter borrow gate trust."""
    statements = Parser(Lexer(source).tokenize()).parse()
    return tuple(summarize_function_effect(item) for item in statements if isinstance(item, ast.FunctionDefinition))
