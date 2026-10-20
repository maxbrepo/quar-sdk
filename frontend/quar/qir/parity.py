"""Opt-in semantic-shape parity check for the supported linear AST subset.

This compares independent lowering routes without modifying compiler defaults.
It is not a proof of whole-program or backend equivalence.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping

from ..ast_nodes import FunctionDefinition
from ..ir.builder import lower_statement
from .ast_lowering import lower_ast_function
from .legacy_bridge import lower_ir_function
from .model import QFunction, QReturn
from .validation import validate_function


class QIRParityError(ValueError):
    """The requested comparison is outside the verified QIR subset."""


@dataclass(frozen=True)
class QIRParityReport:
    equivalent: bool
    direct: QFunction
    bridged: QFunction
    differences: tuple[str, ...]


def _signature(function: QFunction) -> tuple:
    """Canonicalize SSA names by definition order; retain types and operands."""
    validate_function(function)
    if len(function.blocks) != 1 or function.blocks[0].phis:
        raise QIRParityError("Only one-block, Phi-free functions can be compared")
    block = function.blocks[0]
    if not isinstance(block.terminator, QReturn) or block.terminator.value is None:
        raise QIRParityError("A value-return is required")
    names: dict[str, int] = {}
    types: list[str] = []
    for parameter in function.parameters:
        if parameter.name in names:
            raise QIRParityError("Duplicate SSA definition")
        names[parameter.name] = len(names)
        types.append(parameter.type.name)
    instructions = []
    for instruction in block.instructions:
        if instruction.result is None or instruction.result.name in names:
            raise QIRParityError("Missing or duplicate SSA result")
        try:
            operands = tuple((names[item.name], item.type.name) for item in instruction.operands)
        except KeyError as exc:
            raise QIRParityError("Operand without earlier definition") from exc
        instructions.append((instruction.opcode, operands, instruction.result.type.name,
                             instruction.immediate, instruction.metadata))
        names[instruction.result.name] = len(names)
    try:
        returned = names[block.terminator.value.name]
    except KeyError as exc:
        raise QIRParityError("Return without definition") from exc
    return (function.name, function.return_type.name, tuple(types),
            tuple(instructions), (returned, block.terminator.value.type.name))


def compare_ast_qir_routes(function: FunctionDefinition, *,
                           type_aliases: Mapping[str, str] | None = None) -> QIRParityReport:
    """Compare AST->QIR and AST->legacy IR->QIR, ignoring generated SSA names.

    Returns both immutable QIR functions and a structural comparison report.
    Unsupported AST/IR constructs propagate explicit lowering errors.
    """
    direct = lower_ast_function(function, type_aliases=type_aliases)
    legacy = lower_statement(function)
    bridged = lower_ir_function(legacy, type_aliases=dict(type_aliases) if type_aliases else None)
    left = _signature(direct)
    right = _signature(bridged)
    labels = ("function name", "return type", "parameter types", "instructions", "return value")
    differences = tuple(label for label, a, b in zip(labels, left, right) if a != b)
    return QIRParityReport(not differences, direct, bridged, differences)
