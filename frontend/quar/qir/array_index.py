"""Index validation contract for fixed-size i32 arrays.

This module validates indices but does not lower memory operations to QIR.
"""
from __future__ import annotations

from dataclasses import dataclass

from .array_layout import QIRArrayLayout


class QIRArrayIndexError(ValueError):
    """Raised when a static array index violates the layout contract."""


@dataclass(frozen=True)
class QIRArrayIndexCheck:
    """A runtime bounds obligation for a nonconstant i32 index."""

    length: int
    lower_bound: int = 0

    def contains(self, index: int) -> bool:
        """Return whether an integer index is within the array bounds."""
        return type(index) is int and self.lower_bound <= index < self.length


def check_constant_index(layout: QIRArrayLayout, index: int) -> int:
    """Return a valid constant index, otherwise raise a bounds error."""
    check = runtime_index_check(layout)
    if not check.contains(index):
        raise QIRArrayIndexError(f"Index {index!r} is outside [0, {layout.length})")
    return index


def runtime_index_check(layout: QIRArrayLayout) -> QIRArrayIndexCheck:
    """Describe the bounds check required for a dynamic array index."""
    if not isinstance(layout, QIRArrayLayout) or type(layout.length) is not int or layout.length <= 0:
        raise QIRArrayIndexError("Invalid fixed-array layout")
    return QIRArrayIndexCheck(layout.length)
