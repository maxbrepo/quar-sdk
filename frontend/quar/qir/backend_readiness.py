"""Conservative QIR backend readiness audit; does not emit executable code.

Capability sets describe the *planned adapter subset*, not verified support in
existing C or QRVM code generators. Fail closed on all unlisted features.
"""
from __future__ import annotations

from dataclasses import dataclass
from .model import QBranch, QFunction, QJump, QReturn
from .validation import validate_function


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
_ADAPTER_TYPES = frozenset({"i32"})
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
        if name not in _ADAPTER_TYPES:
            issues.append(BackendIssue(label, "type", f"Unsupported adapter type: {name}"))

    check_type("<signature>", function.return_type.name)
    for param in function.parameters:
        check_type("<signature>", param.type.name)
    if len(function.blocks) != 1:
        issues.append(BackendIssue("<function>", "cfg", "Initial adapter requires one basic block"))
    for block in function.blocks:
        if block.phis:
            issues.append(BackendIssue(block.label, "phi", "Phi lowering is not implemented"))
        for instr in block.instructions:
            if instr.opcode not in _ADAPTER_OPERATIONS:
                issues.append(BackendIssue(block.label, "opcode", f"Unsupported adapter opcode: {instr.opcode}"))
            if instr.result is not None:
                check_type(block.label, instr.result.type.name)
            for operand in instr.operands:
                check_type(block.label, operand.type.name)
            if instr.metadata is not None and instr.metadata.safety.checks:
                issues.append(BackendIssue(block.label, "safety", "Safety obligations need runtime lowering"))
        if isinstance(block.terminator, (QJump, QBranch)):
            issues.append(BackendIssue(block.label, "terminator", "Control-flow lowering is not implemented"))
        elif isinstance(block.terminator, QReturn) and block.terminator.value is None:
            issues.append(BackendIssue(block.label, "terminator", "Void return is not in the initial adapter subset"))
    return BackendReadiness(backend, not issues, tuple(issues))
