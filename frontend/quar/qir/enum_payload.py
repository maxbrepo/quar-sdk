"""Compile-time payload contracts shared by language frontends.

This module deliberately does not define a binary ABI or allocate runtime values.
It verifies the information required before lowering tagged payload operations.
"""
from __future__ import annotations

from dataclasses import dataclass

from .enum_layout import QEnumLayout, QIREnumLayoutError
from .model import QType


@dataclass(frozen=True)
class QEnumPayloadContract:
    """A validated variant's tag and ordered payload types."""

    enum_name: str
    variant_name: str
    tag: int
    types: tuple[QType, ...]

    def validate_arguments(self, arguments: tuple[QType, ...]) -> None:
        """Reject construction with incorrect arity or types; return None."""
        if arguments != self.types:
            raise QIREnumLayoutError(
                f"Invalid arguments for {self.enum_name}.{self.variant_name}: "
                f"expected {self.types}, got {arguments}"
            )

    def bind(self, names: tuple[str, ...]) -> tuple[tuple[str, QType], ...]:
        """Validate pattern bindings and return ordered name/type pairs."""
        if len(names) != len(self.types):
            raise QIREnumLayoutError(
                f"Invalid binding count for {self.enum_name}.{self.variant_name}"
            )
        if any(not isinstance(name, str) or not name.strip() for name in names):
            raise QIREnumLayoutError("Binding names must be nonempty strings")
        if len(set(names)) != len(names):
            raise QIREnumLayoutError("Duplicate names in variant bindings")
        return tuple(zip(names, self.types))


def payload_contract(layout: QEnumLayout, variant_name: str) -> QEnumPayloadContract:
    """Resolve a variant using a shared AST/IR enum layout; return its contract."""
    if not isinstance(layout, QEnumLayout):
        raise QIREnumLayoutError("Expected a validated enum layout")
    variant = layout.variant(variant_name)
    return QEnumPayloadContract(
        layout.name, variant.name, variant.tag,
        tuple(QType(type_name) for type_name in variant.payload_types),
    )
