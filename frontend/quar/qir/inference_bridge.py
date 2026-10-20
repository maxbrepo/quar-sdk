"""Conservative typed/inferred/mixed convergence for direct QIR lowering.

This is a small, opt-in AST normalization boundary, not a replacement for
frontend semantic analysis. It never mutates the input AST.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace

from ..ast_nodes import (Assignment, BinaryOperation, FunctionDefinition, Integer,
                         ReturnStatement, Variable, VariableDeclaration)
from .ast_lowering import QIRASTLoweringError, lower_ast_function
from .model import QFunction, QType
from .type_normalization import QIRTypeNormalizationError, normalize_ir_type
from .types import is_integer


class QIRInferenceError(ValueError):
    """The supported AST subset cannot be assigned unambiguous integer types."""


def lower_resolved_ast_function(function: FunctionDefinition, *,
                                type_aliases: Mapping[str, str] | None = None) -> QFunction:
    """Resolve inferred local declarations, then lower through the canonical QIR path.

    Inferred locals use var_type=None or 'auto'. Integer-only expressions are
    assigned i32; expressions containing typed variables inherit that type.
    Function signatures must already have explicit types. Returns validated QIR.
    """
    if not isinstance(function, FunctionDefinition):
        raise QIRInferenceError("Expected a function definition")

    def canonical(name: str) -> QType:
        try:
            result = normalize_ir_type(name, type_aliases)
        except (QIRTypeNormalizationError, TypeError, AttributeError) as exc:
            raise QIRInferenceError(f"Unknown type: {name!r}") from exc
        if not is_integer(result):
            raise QIRInferenceError("Only integer types are supported")
        return result

    if not isinstance(function.return_type, str) or function.return_type == "auto":
        raise QIRInferenceError("Function return type must be explicit")
    canonical(function.return_type)
    scope: dict[str, QType] = {}
    for param in function.parameters:
        if not isinstance(param.var_type, str) or param.var_type == "auto":
            raise QIRInferenceError("Parameter types must be explicit")
        if param.name in scope:
            raise QIRInferenceError(f"Duplicate parameter: {param.name!r}")
        scope[param.name] = canonical(param.var_type)

    def infer(node: object) -> QType:
        if isinstance(node, Integer) and type(node.value) is int:
            return QType("i32")
        if isinstance(node, Variable):
            if node.name not in scope:
                raise QIRInferenceError(f"Unknown variable: {node.name!r}")
            return scope[node.name]
        if isinstance(node, BinaryOperation) and node.operator in ("+", "-", "*"):
            left = infer(node.left)
            right = infer(node.right)
            if left != right:
                # A literal can adopt the type of the other operand; this
                # is contextual literal typing, not implicit variable casting.
                if isinstance(node.left, Integer):
                    return right
                if isinstance(node.right, Integer):
                    return left
                raise QIRInferenceError("Mixed integer types require explicit conversion")
            return left
        raise QIRInferenceError(f"Unsupported expression: {type(node).__name__}")

    normalized_body = []
    for statement in function.body:
        if isinstance(statement, VariableDeclaration):
            if statement.name in scope:
                raise QIRInferenceError(f"Duplicate declaration: {statement.name!r}")
            if statement.var_type is None or statement.var_type == "auto":
                resolved = infer(statement.value)
                normalized_body.append(replace(statement, var_type=resolved.name))
            else:
                resolved = canonical(statement.var_type)
                normalized_body.append(statement)
            scope[statement.name] = resolved
        elif isinstance(statement, Assignment):
            if statement.name not in scope:
                raise QIRInferenceError(f"Unknown assignment target: {statement.name!r}")
            normalized_body.append(statement)
        elif isinstance(statement, ReturnStatement):
            normalized_body.append(statement)
        else:
            raise QIRInferenceError(f"Unsupported statement: {type(statement).__name__}")
    try:
        return lower_ast_function(replace(function, body=normalized_body), type_aliases=type_aliases)
    except QIRASTLoweringError as exc:
        raise QIRInferenceError(str(exc)) from exc
