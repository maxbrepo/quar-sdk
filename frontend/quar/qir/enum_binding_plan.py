"""Frontend-independent binding plans for tagged enum match arms.

Plans describe validated flattened ABI slots, not memory layout or ownership.
"""
from __future__ import annotations

from dataclasses import dataclass

from .enum_layout import QEnumLayout, QIREnumLayoutError
from .enum_payload import payload_contract
from .model import QType


@dataclass(frozen=True)
class QEnumBinding:
    """A name bound to one payload slot, guarded by the active variant tag."""

    name: str
    type: QType
    slot: str


@dataclass(frozen=True)
class QEnumArmPlan:
    variant_name: str
    tag: int
    bindings: tuple[QEnumBinding, ...]


def plan_match_bindings(layout: QEnumLayout, arms: object) -> tuple[QEnumArmPlan, ...]:
    """Validate AST/IR match arms and return ordered, typed slot bindings.

    Slot names follow the experimental flattened calling convention. The
    caller must check the tag before accessing a slot; this plan does not
    generate control flow or imply a stable enum ABI.
    """
    if not isinstance(layout, QEnumLayout) or not isinstance(arms, (tuple, list)):
        raise QIREnumLayoutError("Expected enum layout and match arms")
    seen: set[str] = set()
    result: list[QEnumArmPlan] = []
    for arm in arms:
        variant_name = getattr(arm, "variant_name", None)
        names = getattr(arm, "bindings", None)
        if not isinstance(variant_name, str) or variant_name in seen:
            raise QIREnumLayoutError("Duplicate or invalid match variant")
        if not isinstance(names, (tuple, list)):
            raise QIREnumLayoutError("Invalid match binding list")
        contract = payload_contract(layout, variant_name)
        typed = contract.bind(tuple(names))
        result.append(QEnumArmPlan(variant_name, contract.tag, tuple(
            QEnumBinding(name, field_type, f"payload_{contract.tag}_{index}")
            for index, (name, field_type) in enumerate(typed)
        )))
        seen.add(variant_name)
    return tuple(result)
