"""Strict, opt-in bridge from the existing executable IR to canonical QIR.

Only straight-line, explicitly typed integer functions are supported. Unsupported
nodes fail closed: the existing IR and its backends remain the default pipeline.
"""
from __future__ import annotations

from ..ir.model import (IRAssign, IRBinary, IRDeclare, IRFunctionDefinition,
                        IRLiteral, IRReference, IRReturn)
from .model import QBlock, QFunction, QInstruction, QReturn, QType, QValue
from .types import is_integer
from .type_normalization import normalize_ir_type, QIRTypeNormalizationError
from .validation import validate_function


class QIRBridgeError(ValueError):
    """The legacy IR construct cannot yet be represented without semantic loss."""


_BINARY = {"+": "add", "-": "sub", "*": "mul"}


def lower_ir_function(
    function: IRFunctionDefinition, *, type_aliases: dict[str, str] | None = None
) -> QFunction:
    """Lower a straight-line integer IR function, validating the resulting QIR.

    Returns an immutable QFunction. Does not change or execute the legacy IR.
    """
    if not isinstance(function, IRFunctionDefinition):
        raise QIRBridgeError("Expected an executable IRFunctionDefinition")
    if not function.name:
        raise QIRBridgeError("Function name cannot be empty")

    def integer_type(name: str) -> QType:
        try:
            result = normalize_ir_type(name, type_aliases)
        except (QIRTypeNormalizationError, AttributeError, TypeError) as exc:
            raise QIRBridgeError(f"Unsupported IR type: {name!r}") from exc
        if not is_integer(result):
            raise QIRBridgeError(f"Bridge supports integer types only: {name!r}")
        return result

    return_type = integer_type(function.return_type)
    parameters = []
    environment: dict[str, QValue] = {}
    instructions: list[QInstruction] = []
    serial = 0
    for name, type_name, default in function.parameters:
        if default is not None:
            raise QIRBridgeError("Default parameters are not supported by the bridge")
        if not name or name in environment:
            raise QIRBridgeError("Duplicate or empty parameter name")
        value = QValue(name, integer_type(type_name))
        parameters.append(value)
        environment[name] = value

    def fresh(qtype: QType) -> QValue:
        nonlocal serial
        serial += 1
        while f"$bridge{serial}" in environment:
            serial += 1
        return QValue(f"$bridge{serial}", qtype)

    def expression(node: object, expected: QType) -> QValue:
        if isinstance(node, IRLiteral) and type(node.value) is int:
            value = fresh(expected)
            instructions.append(QInstruction("const", (), value, node.value))
            return value
        if isinstance(node, IRReference):
            if node.name not in environment:
                raise QIRBridgeError(f"Unknown IR reference: {node.name!r}")
            value = environment[node.name]
            if value.type != expected:
                raise QIRBridgeError("Implicit type conversion is not supported")
            return value
        if isinstance(node, IRBinary) and node.operator in _BINARY:
            left = expression(node.left, expected)
            right = expression(node.right, expected)
            value = fresh(expected)
            instructions.append(QInstruction(_BINARY[node.operator], (left, right), value))
            return value
        raise QIRBridgeError(f"Unsupported IR expression: {type(node).__name__}")

    terminator = None
    for index, statement in enumerate(function.body):
        if isinstance(statement, IRDeclare):
            if not statement.name or statement.name in environment:
                raise QIRBridgeError("Duplicate or empty local declaration")
            qtype = integer_type(statement.type_name)
            environment[statement.name] = expression(statement.value, qtype)
        elif isinstance(statement, IRAssign):
            if statement.name not in environment:
                raise QIRBridgeError(f"Assignment to undeclared name: {statement.name!r}")
            environment[statement.name] = expression(statement.value, environment[statement.name].type)
        elif isinstance(statement, IRReturn):
            if index != len(function.body) - 1:
                raise QIRBridgeError("Statements after return are unsupported")
            terminator = QReturn(expression(statement.value, return_type))
        else:
            raise QIRBridgeError(f"Unsupported IR statement: {type(statement).__name__}")
    if terminator is None:
        raise QIRBridgeError("A final return statement is required")
    result = QFunction(function.name, return_type, tuple(parameters),
                       (QBlock("entry", tuple(instructions), terminator),))
    try:
        validate_function(result)
    except ValueError as exc:
        raise QIRBridgeError(f"Generated QIR failed validation: {exc}") from exc
    return result
