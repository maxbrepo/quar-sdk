"""Minimal typed control-flow QIR. Immutable nodes; no runtime dependency."""
from dataclasses import dataclass

@dataclass(frozen=True)
class QType:
    name: str

@dataclass(frozen=True)
class QValue:
    name: str
    type: QType

@dataclass(frozen=True)
class QSourceLocation:
    """One-based source position; file names are logical source identifiers."""
    file: str
    line: int
    column: int

@dataclass(frozen=True)
class QSafetyMetadata:
    """Safety obligations carried by QIR, not assertions of proven safety."""
    checks: tuple[str, ...] = ()
    inspector_tags: tuple[str, ...] = ()

@dataclass(frozen=True)
class QMetadata:
    """Optional diagnostic and safety provenance for a QIR operation."""
    source: QSourceLocation | None = None
    safety: QSafetyMetadata = QSafetyMetadata()

@dataclass(frozen=True)
class QInstruction:
    opcode: str
    operands: tuple[QValue, ...] = ()
    result: QValue | None = None
    immediate: int | None = None
    metadata: QMetadata | None = None

@dataclass(frozen=True)
class QReturn:
    value: QValue | None = None

@dataclass(frozen=True)
class QJump:
    target: str

@dataclass(frozen=True)
class QBranch:
    condition: QValue
    true_target: str
    false_target: str

@dataclass(frozen=True)
class QPhi:
    """Merge edge-specific SSA values at a basic block entry.

    Each incoming pair is (predecessor block label, value).
    """
    result: QValue
    incoming: tuple[tuple[str, QValue], ...]
    metadata: QMetadata | None = None

QTerminator = QReturn | QJump | QBranch

@dataclass(frozen=True)
class QBlock:
    label: str
    instructions: tuple[QInstruction, ...]
    terminator: QTerminator
    phis: tuple[QPhi, ...] = ()

@dataclass(frozen=True)
class QFunction:
    name: str
    return_type: QType
    parameters: tuple[QValue, ...]
    blocks: tuple[QBlock, ...]

@dataclass(frozen=True)
class QModule:
    name: str
    functions: tuple[QFunction, ...]
