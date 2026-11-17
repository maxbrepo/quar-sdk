"""Experimental flattened enum payload projection into canonical QIR.

This is an explicit primitive-value calling convention, NOT a stable enum ABI.
The caller supplies a validated tag and one payload slot per declared field.
A default result is mandatory for invalid tags; inactive slots are never read.
"""
from __future__ import annotations

from .enum_layout import QEnumLayout, QIREnumLayoutError
from .enum_payload import payload_contract
from .model import QBlock, QBranch, QFunction, QInstruction, QReturn, QType, QValue
from .validation import validate_function


def lower_payload_projection(name: str, layout: QEnumLayout, variant_name: str,
                             field_index: int, default: int) -> QFunction:
    """Return an i32 field from one variant, or an explicit i32 default.

    Only primitive i32/bool payload slots are supported. This is a bridge
    toward general match binding, not MatchStatement lowering or enum storage.
    """
    if not isinstance(layout, QEnumLayout) or not layout.variants:
        raise QIREnumLayoutError("Expected a nonempty enum layout")
    contract = payload_contract(layout, variant_name)
    if type(field_index) is not int or not 0 <= field_index < len(contract.types):
        raise QIREnumLayoutError("Invalid payload field index")
    if contract.types[field_index] != QType("i32"):
        raise QIREnumLayoutError("Projection currently requires an i32 field")
    if type(default) is not int or not -(2**31) <= default < 2**31:
        raise QIREnumLayoutError("Default must fit i32")
    if any(field not in (QType("i32"), QType("bool"))
           for variant in layout.variants
           for field in payload_contract(layout, variant.name).types):
        raise QIREnumLayoutError("Unsupported payload slot type")

    i32, boolean = QType("i32"), QType("bool")
    tag = QValue("enum_tag", i32)
    # All slots are passed explicitly. No packed enum or ownership is implied.
    parameters = [tag]
    selected = None
    for variant in layout.variants:
        for index, field_type in enumerate(payload_contract(layout, variant.name).types):
            value = QValue(f"payload_{variant.tag}_{index}", field_type)
            parameters.append(value)
            if variant.name == variant_name and index == field_index:
                selected = value
    assert selected is not None
    expected_tag = QValue("expected_tag", i32)
    condition = QValue("variant_active", boolean)
    fallback = QValue("fallback", i32)
    blocks = (
        QBlock("entry", (
            QInstruction("const", (), expected_tag, contract.tag),
            QInstruction("eq", (tag, expected_tag), condition),
        ), QBranch(condition, "selected", "invalid")),
        QBlock("selected", (), QReturn(selected)),
        QBlock("invalid", (QInstruction("const", (), fallback, default),), QReturn(fallback)),
    )
    function = QFunction(name, i32, tuple(parameters), blocks)
    validate_function(function)
    return function
