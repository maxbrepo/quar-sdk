"""Experimental tag-only enum dispatch into canonical QIR control flow.

This is a backend-oriented primitive, not the general AST MatchStatement lowering.
The caller must supply a previously validated enum layout and explicit arm values.
"""
from __future__ import annotations

from .enum_layout import QEnumLayout, QIREnumLayoutError
from .model import QBlock, QBranch, QFunction, QInstruction, QJump, QReturn, QType, QValue
from .validation import validate_function


def lower_tag_dispatch(name: str, layout: QEnumLayout, arms: dict[str, int], default: int | None = None) -> QFunction:
    """Build a validated i32 function mapping an enum tag to an i32 result.

    Reject payload-bearing enums until their runtime representation is defined.
    A missing arm is permitted only with an explicit default value.
    Returns a QFunction whose sole parameter is the internal enum tag.
    """
    if not isinstance(layout, QEnumLayout) or not layout.variants:
        raise QIREnumLayoutError("Expected a nonempty enum layout")
    if any(variant.payload_types for variant in layout.variants):
        raise QIREnumLayoutError("Payload-bearing enum dispatch is not supported")
    known = {variant.name for variant in layout.variants}
    if not isinstance(arms, dict) or not set(arms).issubset(known):
        raise QIREnumLayoutError("Unknown enum arm")
    if default is None and set(arms) != known:
        raise QIREnumLayoutError("Non-exhaustive enum dispatch")
    if any(type(value) is not int or not -(2**31) <= value < 2**31 for value in arms.values()):
        raise QIREnumLayoutError("Arm result must fit i32")
    if default is not None and (type(default) is not int or not -(2**31) <= default < 2**31):
        raise QIREnumLayoutError("Default result must fit i32")
    i32 = QType("i32")
    boolean = QType("bool")
    tag = QValue("enum_tag", i32)
    blocks: list[QBlock] = []
    for index, variant in enumerate(layout.variants):
        label = f"check_{index}"
        if variant.name not in arms:
            # An explicit default handles this variant and any unrecognized tag.
            blocks.append(QBlock(label, (), QJump("default")))
            continue
        constant = QValue(f"tag_{index}", i32)
        condition = QValue(f"matches_{index}", boolean)
        next_label = f"check_{index + 1}" if index + 1 < len(layout.variants) else "default"
        blocks.append(QBlock(label, (
            QInstruction("const", (), constant, variant.tag),
            QInstruction("eq", (tag, constant), condition),
        ), QBranch(condition, f"arm_{index}", next_label)))
        result = QValue(f"result_{index}", i32)
        blocks.append(QBlock(f"arm_{index}", (QInstruction("const", (), result, arms[variant.name]),), QReturn(result)))
    # Even exhaustive source matches need a defensive invalid-tag path.
    # This initial primitive returns a deterministic sentinel, not a runtime trap.
    fallback = default if default is not None else 0
    fallback_value = QValue("default_result", i32)
    blocks.append(QBlock("default", (QInstruction("const", (), fallback_value, fallback),), QReturn(fallback_value)))
    function = QFunction(name, i32, (tag,), tuple(blocks))
    validate_function(function)
    return function
