"""Fail-closed migration evidence for the experimental QIR pipeline.

A successful adapter check is NOT evidence that the production backend is ready.
The legacy IR must remain in service until independent integration evidence exists.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Iterable

from .backend_readiness import inspect_backend_readiness
from .model import QFunction


@dataclass(frozen=True)
class MigrationEvidence:
    """Explicitly recorded integration results; defaults never claim success."""
    typed_verified: bool = False
    inferred_verified: bool = False
    mixed_verified: bool = False
    control_flow_verified: bool = False
    memory_safety_verified: bool = False
    c_production_verified: bool = False
    qrvm_production_verified: bool = False
    functional_regressions_verified: bool = False
    dependency_audit_verified: bool = False


@dataclass(frozen=True)
class MigrationGateReport:
    can_remove_legacy_ir: bool
    blockers: tuple[str, ...]
    inspected_functions: int


_REQUIRED_EVIDENCE = (
    "typed_verified", "inferred_verified", "mixed_verified",
    "control_flow_verified", "memory_safety_verified",
    "c_production_verified", "qrvm_production_verified",
    "functional_regressions_verified", "dependency_audit_verified",
)


def inspect_migration_gate(functions: Iterable[QFunction],
                           evidence: MigrationEvidence | None = None) -> MigrationGateReport:
    """Audit candidate QIR functions and explicit external migration evidence.

    This is a planning gate, not an independent proof of backend equivalence.
    An empty sample cannot authorize removal. Invalid QIR propagates an error.
    """
    evidence = evidence if evidence is not None else MigrationEvidence()
    blockers = [f"missing evidence: {name}" for name in _REQUIRED_EVIDENCE
                if not getattr(evidence, name)]
    count = 0
    for count, function in enumerate(functions, 1):
        # Both profiles describe the planned small adapter subset, not production support.
        for backend in ("c", "qrvm"):
            readiness = inspect_backend_readiness(function, backend)
            for issue in readiness.issues:
                blockers.append(f"function {count} ({function.name}) / {backend} / "
                                f"{issue.block}: {issue.feature}: {issue.reason}")
    if count == 0:
        blockers.append("no QIR functions supplied for audit")
    return MigrationGateReport(not blockers, tuple(blockers), count)
