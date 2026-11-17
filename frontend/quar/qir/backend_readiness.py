"""Conservative QIR backend readiness audit; does not emit executable code.

Capability sets describe the *planned adapter subset*, not verified support in
existing C or QRVM code generators. Fail closed on all unlisted features.
"""
from __future__ import annotations

from dataclasses import dataclass
from .model import QBranch, QFunction, QJump, QReturn
from .validation import validate_function
from .cast_safety import assess_integer_cast


@dataclass(frozen=True)
class BackendIssue:
    block: str
    feature: str
    reason: str


@dataclass(frozen=True)
class BackendReadiness:
    backend: str
    ready_for_adapter: bool
    issues: tuple[BackendIssue, ...]


# These are proposed first-adapter contracts, NOT existing backend guarantees.
_ADAPTER_OPERATIONS = frozenset({"const", "copy", "add", "sub", "mul"})
_C_OPERATIONS = _ADAPTER_OPERATIONS | frozenset({"div", "mod", "eq", "ne", "lt", "le", "gt", "ge", "bit_and", "bit_or", "bit_xor", "bit_not", "shl", "shr", "logical_not", "cast", "array_alloc", "array_get", "array_set", "string_byte_len", "string_scalar_len", "string_scalar_at", "string_const"})
_ADAPTER_TYPES = frozenset({"i32"})
_C_CAST_TYPES = frozenset({"i8", "u8", "i16", "u16"})
_BACKENDS = frozenset({"c", "qrvm"})


def inspect_backend_readiness(function: QFunction, backend: str) -> BackendReadiness:
    """Check a QIR function against the initial proposed backend adapter subset.

    Returns explicit issues for every unsupported operation, type, CFG or
    safety obligation. Does not imply runtime equivalence or backend support.
    """
    if backend not in _BACKENDS:
        raise ValueError(f"Unknown backend: {backend!r}")
    validate_function(function)
    issues: list[BackendIssue] = []

    def check_type(label: str, name: str) -> None:
        if name not in ({"ptr<i32>", "string"} if backend == "c" else set()) | (_ADAPTER_TYPES | ({"bool"} | _C_CAST_TYPES if backend == "c" else set())):
            issues.append(BackendIssue(label, "type", f"Unsupported adapter type: {name}"))

    check_type("<signature>", function.return_type.name)
    for param in function.parameters:
        check_type("<signature>", param.type.name)
    if len(function.blocks) != 1 and backend != "c":
        issues.append(BackendIssue("<function>", "cfg", "Initial adapter requires one basic block"))
    for block in function.blocks:
        if block.phis and backend != "c":
            issues.append(BackendIssue(block.label, "phi", "Phi lowering is not implemented"))
        for instr in block.instructions:
            if instr.opcode not in (_C_OPERATIONS if backend == "c" else _ADAPTER_OPERATIONS):
                issues.append(BackendIssue(block.label, "opcode", f"Unsupported adapter opcode: {instr.opcode}"))
            if backend == "c":
                if instr.opcode == "cast":
                    source = instr.operands[0].type.name
                    target = instr.result.type.name
                    if (source not in (_C_CAST_TYPES | {"i32"}) or
                            target not in (_C_CAST_TYPES | {"i32"})):
                        issues.append(BackendIssue(block.label, "cast", "Only i8/u8/i16/u16/i32 casts are supported"))
                    else:
                        assess_integer_cast(instr.operands[0].type, instr.result.type)
                elif instr.opcode not in {"const", "copy", "array_alloc", "array_get", "array_set", "string_byte_len", "string_scalar_len", "string_scalar_at", "string_const"} and any(
                    value.type.name not in {"i32", "bool"}
                    for value in (*instr.operands, instr.result)
                ):
                    issues.append(BackendIssue(block.label, "type", "Non-i32 arithmetic is not supported"))
            if instr.result is not None:
                check_type(block.label, instr.result.type.name)
            for operand in instr.operands:
                check_type(block.label, operand.type.name)
            if instr.metadata is not None and instr.metadata.safety.checks and not (backend == "c" and ((instr.opcode == "cast" and set(instr.metadata.safety.checks) <= {"cast"}) or (instr.opcode in {"array_get", "array_set"} and set(instr.metadata.safety.checks) <= {"bounds"}) or (instr.opcode in {"string_byte_len", "string_scalar_len", "string_scalar_at"} and set(instr.metadata.safety.checks) <= {"string_length", "bounds"}))):
                issues.append(BackendIssue(block.label, "safety", "Safety obligations need runtime lowering"))
        if isinstance(block.terminator, (QJump, QBranch)) and backend != "c":
            issues.append(BackendIssue(block.label, "terminator", "Control-flow lowering is not implemented"))
        elif isinstance(block.terminator, QReturn) and block.terminator.value is None:
            issues.append(BackendIssue(block.label, "terminator", "Void return is not in the initial adapter subset"))
    return BackendReadiness(backend, not issues, tuple(issues))
