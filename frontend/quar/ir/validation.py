"""Structural validation for backend-independent Quar IR."""
from dataclasses import fields, is_dataclass
from .model import IRCall, IRProject


class IRValidationError(ValueError):
    """Raised when IR contains an inconsistent symbol or module reference."""


def validate_project(project: IRProject) -> None:
    """Validate unique identities, dependencies and internal function calls."""
    modules = {module.module_id: module for module in project.modules}
    if len(modules) != len(project.modules):
        raise IRValidationError("Duplicate module identity")
    symbols = [function.symbol for module in project.modules for function in module.functions]
    if len(symbols) != len(set(symbols)):
        raise IRValidationError("Duplicate function identity")
    available = set(symbols)
    if project.entry_module is not None:
        if project.entry_module not in modules:
            raise IRValidationError(f"Missing entry module: {project.entry_module}")
        for statement in project.entry_body:
            _check_calls(statement, available)
    for module in project.modules:
        for dependency in module.dependencies:
            if dependency not in modules:
                raise IRValidationError(f"Missing module dependency: {dependency}")
        for function in module.functions:
            if not function.symbol.startswith(module.module_id + "::"):
                raise IRValidationError(f"Invalid function identity: {function.symbol}")
            for statement in function.body:
                _check_calls(statement, available)


def _check_calls(node, available):
    """Validate calls recursively, including nested control-flow and operands.

    Traversal is structural so newly introduced immutable IR nodes are
    covered without requiring a parallel list of supported statements.
    """
    if isinstance(node, IRCall) and node.symbol not in available:
        raise IRValidationError(f"Unknown function symbol: {node.symbol}")
    if isinstance(node, (tuple, list)):
        for item in node:
            _check_calls(item, available)
    elif is_dataclass(node) and not isinstance(node, type):
        for field in fields(node):
            _check_calls(getattr(node, field.name), available)
