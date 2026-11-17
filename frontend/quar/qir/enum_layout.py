"""Canonical enum tag layout for future QIR tagged-value lowering.

This module defines a compile-time contract only; it does not encode runtime payloads.
"""
from dataclasses import dataclass


class QIREnumLayoutError(ValueError):
    """Raised for invalid or ambiguous enum declarations."""


@dataclass(frozen=True)
class QEnumVariantLayout:
    name: str
    tag: int
    payload_types: tuple[str, ...]


@dataclass(frozen=True)
class QEnumLayout:
    name: str
    variants: tuple[QEnumVariantLayout, ...]

    def variant(self, name: str) -> QEnumVariantLayout:
        """Return the named variant or reject an unknown name."""
        for variant in self.variants:
            if variant.name == name:
                return variant
        raise QIREnumLayoutError(f"Unknown variant {self.name}.{name}")


def lower_enum_layout(definition: object) -> QEnumLayout:
    """Assign stable declaration-order tags to AST or legacy IR enum variants.

    Tags are internal and deterministic for a given declaration; no ABI is promised.
    """
    name = getattr(definition, "name", None)
    members = getattr(definition, "members", None)
    if not isinstance(name, str) or not name.strip() or not isinstance(members, (list, tuple)):
        raise QIREnumLayoutError("Invalid enum declaration")
    if not members:
        raise QIREnumLayoutError(f"Enum {name} must contain at least one variant")
    seen: set[str] = set()
    variants: list[QEnumVariantLayout] = []
    for tag, member in enumerate(members):
        variant_name = getattr(member, "name", None)
        payload = getattr(member, "payload_types", None)
        if not isinstance(variant_name, str) or not variant_name.strip():
            raise QIREnumLayoutError("Invalid enum variant name")
        if variant_name in seen:
            raise QIREnumLayoutError(f"Duplicate enum variant {name}.{variant_name}")
        if not isinstance(payload, (list, tuple)) or any(
            not isinstance(item, str) or not item.strip() for item in payload
        ):
            raise QIREnumLayoutError(f"Invalid payload types for {name}.{variant_name}")
        seen.add(variant_name)
        variants.append(QEnumVariantLayout(variant_name, tag, tuple(payload)))
    return QEnumLayout(name, tuple(variants))
