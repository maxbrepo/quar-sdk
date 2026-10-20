"""Initial typed QIR operations; no implicit conversions or backend coupling."""
from __future__ import annotations

from .model import QInstruction
from .types import canonical_type, is_numeric, is_integer, pointee_type


class QIROperationError(ValueError):
    """Raised for malformed or unsupported QIR operations."""


def validate_instruction(instruction: QInstruction) -> None:
    """Validate supported value operations and their exact operand types."""
    op = instruction.opcode
    operands = instruction.operands
    result = instruction.result
    try:
        for value in operands:
            canonical_type(value.type.name)
        if result is not None:
            canonical_type(result.type.name)
    except ValueError as exc:
        raise QIROperationError(str(exc)) from exc

    if op == "const":
        valid = (not operands and result is not None and is_integer(result.type)
                 and type(instruction.immediate) is int and
                 _fits_integer(instruction.immediate, result.type.name))
    elif instruction.immediate is not None:
        valid = False
    elif op == "alloca":
        valid = len(operands) == 0 and result is not None and result.type.name.startswith("ptr<")
    elif op == "load":
        valid = len(operands) == 1 and result is not None and (
            operands[0].type.name.startswith("ptr<") and
            pointee_type(operands[0].type) == result.type
        )
    elif op == "store":
        valid = len(operands) == 2 and result is None and (
            operands[0].type.name.startswith("ptr<") and
            pointee_type(operands[0].type) == operands[1].type
        )
    elif op == "cast":
        # Explicit numeric conversion only; narrowing is permitted but must
        # be checked by the lowering/runtime safety policy before execution.
        valid = (len(operands) == 1 and result is not None and
                 is_numeric(operands[0].type) and is_numeric(result.type))
    elif op == "copy":
        valid = len(operands) == 1 and result is not None and result.type == operands[0].type
    elif op in ("add", "sub", "mul", "div"):
        valid = (len(operands) == 2 and result is not None
                 and is_numeric(result.type)
                 and all(value.type == result.type for value in operands))
    elif op in ("eq", "ne", "lt", "le", "gt", "ge"):
        valid = (len(operands) == 2 and result is not None
                 and result.type.name == "bool"
                 and operands[0].type == operands[1].type
                 and (op in ("eq", "ne") or is_numeric(operands[0].type))
                 and operands[0].type.name != "void")
    else:
        raise QIROperationError(f"Unsupported QIR opcode: {op!r}")
    if not valid:
        raise QIROperationError(f"Invalid operands or result for QIR opcode: {op!r}")


def _fits_integer(value: int, name: str) -> bool:
    """Return whether an integer fits the exact signed or unsigned QIR width."""
    width = int(name[1:])
    if name.startswith("u"):
        return 0 <= value < (1 << width)
    return -(1 << (width - 1)) <= value < (1 << (width - 1))
