"""Experimental typed enum values for the QIR bootstrap runtime.

This is a language-neutral value model, not a binary ABI or QIR instruction.
Only i32 and bool payloads are supported; references and ownership are deferred.
"""
from __future__ import annotations

from dataclasses import dataclass

from .enum_layout import QEnumLayout, QIREnumLayoutError
from .enum_payload import payload_contract
from .model import QType


@dataclass(frozen=True)
class QEnumRuntimeValue:
    """An immutable tagged value with validated, ordered primitive payloads."""

    layout: QEnumLayout
    tag: int
    payload: tuple[int | bool, ...]

    def variant_name(self) -> str:
        """Return the variant name associated with this value's tag."""
        for variant in self.layout.variants:
            if variant.tag == self.tag:
                return variant.name
        raise QIREnumLayoutError("Invalid enum tag")

    def matches(self, variant_name: str) -> bool:
        """Return whether the value has the requested variant."""
        return self.tag == payload_contract(self.layout, variant_name).tag

    def bindings(self, variant_name: str, names: tuple[str, ...]) -> dict[str, int | bool]:
        """Extract typed bindings only when the requested variant is active."""
        contract = payload_contract(self.layout, variant_name)
        pairs = contract.bind(names)
        if self.tag != contract.tag:
            raise QIREnumLayoutError("Cannot bind payload of an inactive variant")
        return dict(zip((name for name, _ in pairs), self.payload))


def construct_enum_value(
    layout: QEnumLayout, variant_name: str, payload: tuple[int | bool, ...] = ()
) -> QEnumRuntimeValue:
    """Validate and construct an immutable enum value; return the tagged value."""
    contract = payload_contract(layout, variant_name)
    if not isinstance(payload, tuple) or len(payload) != len(contract.types):
        raise QIREnumLayoutError("Invalid enum payload arity")
    for expected, value in zip(contract.types, payload):
        if expected == QType("bool"):
            valid = type(value) is bool
        elif expected == QType("i32"):
            valid = type(value) is int and -(2**31) <= value < 2**31
        else:
            raise QIREnumLayoutError(f"Unsupported runtime payload type: {expected.name}")
        if not valid:
            raise QIREnumLayoutError(f"Invalid value for payload type {expected.name}")
    return QEnumRuntimeValue(layout, contract.tag, payload)
