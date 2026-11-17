"""Conservative array layout contract for future indexed-memory lowering.

This module does not emit QIR memory operations or claim runtime bounds safety.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..ast_nodes import ArrayDeclaration, Integer
from ..ir.model import IRArrayNew, IRLiteral


class QIRArrayLayoutError(ValueError):
    """Raised when an array cannot use the initial fixed-i32 layout."""


@dataclass(frozen=True)
class QIRArrayLayout:
    """Fixed one-dimensional i32 storage requirements, in elements."""

    name: str
    length: int
    initial_values: tuple[int, ...]


def analyze_array_layout(declaration: ArrayDeclaration | IRArrayNew) -> QIRArrayLayout:
    """Validate a static i32 array and return its deterministic layout."""
    if not isinstance(declaration, (ArrayDeclaration, IRArrayNew)):
        raise QIRArrayLayoutError("Expected an array declaration")
    if declaration.element_type != "i32":
        raise QIRArrayLayoutError("Only i32 array elements are supported")
    if declaration.dynamic or declaration.second_size is not None:
        raise QIRArrayLayoutError("Dynamic and multidimensional arrays are not supported")
    length = declaration.size
    if type(length) is not int or length <= 0:
        raise QIRArrayLayoutError("Array length must be a positive integer")
    if length > 1_000_000:
        raise QIRArrayLayoutError("Array length exceeds the initial layout limit")
    values = declaration.initial_values
    if values is None:
        raise QIRArrayLayoutError("Initial layout requires explicit element initialization")
    if len(values) != length:
        raise QIRArrayLayoutError("Initializer count must equal array length")
    result: list[int] = []
    for item in values:
        if isinstance(item, Integer):
            value = item.value
        elif isinstance(item, IRLiteral):
            value = item.value
        else:
            raise QIRArrayLayoutError("Initializers must be integer literals")
        if type(value) is not int or not -(2**31) <= value < 2**31:
            raise QIRArrayLayoutError("Initializer must fit in signed i32")
        result.append(value)
    return QIRArrayLayout(declaration.name, length, tuple(result))
