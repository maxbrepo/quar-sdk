"""Canonical primitive QIR types; aggregate types are deferred to later blocks."""
from __future__ import annotations

from .model import QType

_POINTER_PREFIX = "ptr<"

_INTEGER_WIDTHS = (8, 16, 32, 64, 128)
_PRIMITIVES = frozenset({"void", "bool", "char", "string", "f32", "f64"} | {
    f"{prefix}{width}" for prefix in ("i", "u") for width in _INTEGER_WIDTHS
})


def canonical_type(name: str) -> QType:
    """Return a validated primitive type; reject aliases and unknown names."""
    if name.startswith(_POINTER_PREFIX) and name.endswith(">"):
        target = name[len(_POINTER_PREFIX):-1]
        if target != "void" and target in _PRIMITIVES:
            return QType(name)
    if name not in _PRIMITIVES:
        raise ValueError(f"Non-canonical or unsupported QIR type: {name!r}")
    return QType(name)


def is_numeric(qtype: QType) -> bool:
    """Return whether the canonical type supports arithmetic operations."""
    return qtype.name in _PRIMITIVES and (
        qtype.name.startswith(("i", "u", "f")) and qtype.name[1:].isdigit()
    )


def is_integer(qtype: QType) -> bool:
    """Return whether the canonical type is a fixed-width integer."""
    return qtype.name in _PRIMITIVES and qtype.name.startswith(("i", "u")) and qtype.name[1:].isdigit()


def pointer_type(pointee: QType) -> QType:
    """Construct a typed pointer; void and nested pointers are deferred."""
    canonical_type(pointee.name)
    if pointee.name == "void" or pointee.name.startswith(_POINTER_PREFIX):
        raise ValueError("Pointer target must be a non-void primitive")
    return QType(f"ptr<{pointee.name}>")

def pointee_type(pointer: QType) -> QType:
    """Return the element type of a canonical pointer."""
    canonical_type(pointer.name)
    if not pointer.name.startswith(_POINTER_PREFIX):
        raise ValueError("Expected a QIR pointer type")
    return QType(pointer.name[len(_POINTER_PREFIX):-1])
