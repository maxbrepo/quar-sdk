"""Explicit legacy type normalization at the IR-to-QIR migration boundary.

The QIR model itself only accepts canonical names. Frontend aliases are
resolved before constructing QIR, never accepted implicitly by QIR validation.
"""
from __future__ import annotations

from collections.abc import Mapping

from ..numeric_types import TYPE_ALIASES
from .model import QType
from .types import canonical_type


class QIRTypeNormalizationError(ValueError):
    """A source type cannot be mapped losslessly to a supported QIR type."""


def normalize_ir_type(name: str, aliases: Mapping[str, str] | None = None) -> QType:
    """Resolve built-in and explicit user aliases to a canonical QIR type.

    User aliases must be supplied explicitly from semantic analysis. Cycles,
    shadowing built-in aliases and unsupported types fail closed. Returns QType.
    """
    if not isinstance(name, str) or not name:
        raise QIRTypeNormalizationError("IR type name must be a nonempty string")
    custom = aliases if aliases is not None else {}
    if any(not isinstance(key, str) or not isinstance(value, str)
           or not key or not value for key, value in custom.items()):
        raise QIRTypeNormalizationError("Invalid custom type alias")
    if set(custom).intersection(TYPE_ALIASES):
        raise QIRTypeNormalizationError("Custom aliases cannot shadow built-in aliases")
    current = name
    visited: set[str] = set()
    while current in custom or current in TYPE_ALIASES:
        if current in visited:
            raise QIRTypeNormalizationError(f"Cyclic IR type alias: {name!r}")
        visited.add(current)
        current = custom[current] if current in custom else TYPE_ALIASES[current]
    try:
        return canonical_type(current)
    except ValueError as exc:
        raise QIRTypeNormalizationError(f"Unsupported IR type: {name!r}") from exc
