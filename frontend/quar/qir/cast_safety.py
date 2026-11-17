"""Classify explicit integer casts before QIR backend lowering.

This module describes representable value ranges; it does not execute casts.
"""
from __future__ import annotations

from dataclasses import dataclass

from .model import QType
from .types import canonical_type, is_integer


@dataclass(frozen=True)
class IntegerCastAssessment:
    source: QType
    target: QType
    requires_runtime_check: bool
    minimum: int
    maximum: int


def integer_range(qtype: QType) -> tuple[int, int]:
    """Return the inclusive range of a canonical fixed-width integer type."""
    canonical_type(qtype.name)
    if not is_integer(qtype):
        raise ValueError(f"Expected an integer type, got {qtype.name!r}")
    bits = int(qtype.name[1:])
    if qtype.name.startswith("u"):
        return 0, (1 << bits) - 1
    return -(1 << (bits - 1)), (1 << (bits - 1)) - 1


def assess_integer_cast(source: QType, target: QType) -> IntegerCastAssessment:
    """Return whether an explicit cast needs a checked runtime range test."""
    source_min, source_max = integer_range(source)
    target_min, target_max = integer_range(target)
    needs_check = source_min < target_min or source_max > target_max
    return IntegerCastAssessment(source, target, needs_check, target_min, target_max)
