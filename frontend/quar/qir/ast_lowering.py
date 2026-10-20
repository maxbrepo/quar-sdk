"""Opt-in direct AST-to-QIR lowering for a strictly typed linear integer subset.

This module does not import the legacy IR. Unsupported constructs fail closed.
"""
from __future__ import annotations

from collections.abc import Mapping

from ..ast_nodes import (Assignment, BinaryOperation, FunctionDefinition, Integer,
                         ReturnStatement, Variable, VariableDeclaration)
from .model import QBlock, QFunction, QInstruction, QReturn, QType, QValue
from .type_normalization import QIRTypeNormalizationError, normalize_ir_type
from .types import is_integer
from .validation import validate_function


class QIRASTLoweringError(ValueError):
    """The source AST is outside the verified direct-lowering subset."""


_OPERATORS = {"+": "add", "-": "sub", "*": "mul"}


def lower_ast_function(function: FunctionDefinition, *,
                       type_aliases: Mapping[str, str] | None = None) -> QFunction:
    """Lower one linear integer AST function directly to validated immutable QIR.

    The caller is responsible for running semantic analysis first. This
    function also checks its own supported subset, types and definitions.
    Returns a QFunction; it never mutates the AST or the legacy IR pipeline.
    """
    if not isinstance(function, FunctionDefinition) or not isinstance(function.name, str) or not function.name:
        raise QIRASTLoweringError("Expected a named AST FunctionDefinition")

    def integer_type(name: str) -> QType:
        try:
            qtype = normalize_ir_type(name, type_aliases)
        except (QIRTypeNormalizationError, TypeError, AttributeError) as exc:
            raise QIRASTLoweringError(f"Unsupported source type: {name!r}") from exc
        if not is_integer(qtype):
            raise QIRASTLoweringError(f"Direct AST lowering supports integer types only: {name!r}")
        return qtype

    result_type = integer_type(function.return_type)
    params: list[QValue] = []
    values: dict[str, QValue] = {}
    declared_types: dict[str, QType] = {}
    instructions: list[QInstruction] = []
    serial = 0

    def fresh(qtype: QType) -> QValue:
        nonlocal serial
        serial += 1
        return QValue(f"$ast{serial}", qtype)

    for parameter in function.parameters:
        if parameter.default_value is not None:
            raise QIRASTLoweringError("Default parameters are unsupported")
        if not isinstance(parameter.name, str) or not parameter.name or parameter.name in values:
            raise QIRASTLoweringError("Duplicate or empty parameter")
        qtype = integer_type(parameter.var_type)
        value = QValue(parameter.name, qtype)
        params.append(value)
        values[parameter.name] = value
        declared_types[parameter.name] = qtype

    def expression(node: object, expected: QType) -> QValue:
        if isinstance(node, Integer) and type(node.value) is int:
            value = fresh(expected)
            instructions.append(QInstruction("const", (), value, node.value))
            return value
        if isinstance(node, Variable):
            if node.name not in values:
                raise QIRASTLoweringError(f"Undefined variable: {node.name!r}")
            value = values[node.name]
            if value.type != expected:
                raise QIRASTLoweringError("Implicit numeric conversion is unsupported")
            return value
        if isinstance(node, BinaryOperation) and node.operator in _OPERATORS:
            left = expression(node.left, expected)
            right = expression(node.right, expected)
            value = fresh(expected)
            instructions.append(QInstruction(_OPERATORS[node.operator], (left, right), value))
            return value
        raise QIRASTLoweringError(f"Unsupported AST expression: {type(node).__name__}")

    terminator = None
    for index, statement in enumerate(function.body):
        if isinstance(statement, VariableDeclaration):
            if not isinstance(statement.name, str) or not statement.name or statement.name in declared_types:
                raise QIRASTLoweringError("Duplicate or empty local declaration")
            qtype = integer_type(statement.var_type)
            value = expression(statement.value, qtype)
            declared_types[statement.name] = qtype
            values[statement.name] = value
        elif isinstance(statement, Assignment):
            if statement.name not in declared_types:
                raise QIRASTLoweringError(f"Assignment to undeclared variable: {statement.name!r}")
            values[statement.name] = expression(statement.value, declared_types[statement.name])
        elif isinstance(statement, ReturnStatement):
            if index != len(function.body) - 1 or statement.value is None:
                raise QIRASTLoweringError("A final value-return is required")
            terminator = QReturn(expression(statement.value, result_type))
        else:
            raise QIRASTLoweringError(f"Unsupported AST statement: {type(statement).__name__}")
    if terminator is None:
        raise QIRASTLoweringError("A final return statement is required")
    result = QFunction(function.name, result_type, tuple(params),
                       (QBlock("entry", tuple(instructions), terminator),))
    try:
        validate_function(result)
    except ValueError as exc:
        raise QIRASTLoweringError(f"Generated QIR failed validation: {exc}") from exc
    return result
