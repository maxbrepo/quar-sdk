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
        valid = (not operands and result is not None and ((is_integer(result.type) and type(instruction.immediate) is int and
                       _fits_integer(instruction.immediate, result.type.name)) or
                      (result.type.name == "bool" and type(instruction.immediate) is bool)))
    elif op == "string_const":
        valid = (not operands and result is not None and result.type.name == "string" and
                 type(instruction.immediate) is str)
    elif instruction.immediate is not None and op not in ("array_alloc", "call", "call_void", "native_call", "native_call_void"):
        valid = False
    elif op == "print":
        # Observable output is a side-effecting, result-free QIR instruction.
        valid = (len(operands) == 1 and result is None and
                 operands[0].type.name in ("i32", "bool") and instruction.immediate is None)
    elif op in ("call", "call_void", "native_call", "native_call_void"):
        # The immediate is a callee symbol, never a numeric constant.
        # Cross-function signature checking is performed by validate_module.
        valid = (type(instruction.immediate) is str and
                 bool(instruction.immediate) and instruction.immediate.isidentifier() and
                 ((result is None) if op in ("call_void", "native_call_void") else (result is not None and result.type.name != "void")) and
                 all(value.type.name != "void" for value in operands))
    elif op in ("string_byte_len", "string_scalar_len"):
        # A length-delimited UTF-8 string is distinct from an array of bytes.
        # Runtime lowering must check that the result fits signed i32.
        valid = (len(operands) == 1 and result is not None and
                 operands[0].type.name == "string" and
                 result.type.name == "i32" and
                 instruction.metadata is not None and
                 "string_length" in instruction.metadata.safety.checks)
    elif op == "string_scalar_at":
        # Index counts Unicode scalar values, not UTF-8 bytes or graphemes.
        valid = (len(operands) == 2 and result is not None and
                 operands[0].type.name == "string" and
                 operands[1].type.name == "i32" and
                 result.type.name == "i32" and
                 instruction.metadata is not None and
                 "string_length" in instruction.metadata.safety.checks and
                 "bounds" in instruction.metadata.safety.checks)
    elif op == "array_alloc":
        valid = (not operands and result is not None and
                 result.type.name == "ptr<i32>" and
                 type(instruction.immediate) is int and
                 0 < instruction.immediate <= 1_000_000)
    elif op == "array_get":
        valid = (len(operands) == 2 and result is not None and
                 operands[0].type.name == "ptr<i32>" and
                 operands[1].type.name == "i32" and result.type.name == "i32" and
                 instruction.metadata is not None and
                 "bounds" in instruction.metadata.safety.checks)
    elif op == "array_set":
        valid = (len(operands) == 3 and result is None and
                 operands[0].type.name == "ptr<i32>" and
                 operands[1].type.name == "i32" and
                 operands[2].type.name == "i32" and
                 instruction.metadata is not None and
                 "bounds" in instruction.metadata.safety.checks)
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
    elif op in ("add", "sub", "mul", "div", "mod"):
        valid = (len(operands) == 2 and result is not None
                 and (is_integer(result.type) if op == "mod" else is_numeric(result.type))
                 and all(value.type == result.type for value in operands))
    elif op in ("bit_and", "bit_or", "bit_xor", "shl", "shr"):
        valid = (len(operands) == 2 and result is not None
                 and is_integer(result.type)
                 and all(value.type == result.type for value in operands))
    elif op == "logical_not":
        valid = (len(operands) == 1 and result is not None
                 and result.type.name == "bool" and operands[0].type == result.type)
    elif op == "bit_not":
        valid = (len(operands) == 1 and result is not None
                 and is_integer(result.type) and operands[0].type == result.type)
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
