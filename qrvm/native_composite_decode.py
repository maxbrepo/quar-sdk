"""Read copied native composite output without exposing native addresses.

Union interpretation requires an explicit member selection supplied by a trusted
binding. This is an ABI decoder, not a Visual Quar source-level value type.
"""
from __future__ import annotations

import ctypes
from qrvm.native_composite_layout import NativeArrayType, NativeCompositeLayout


class NativeCompositeDecodeError(ValueError):
    """Indicate an invalid ABI buffer or ambiguous union selection."""


def decode_composite(raw: bytes, layout: NativeCompositeLayout, *, union_members: dict[str, str] | None = None) -> dict[str, object]:
    """Decode an exact-size ABI copy into Python values; return no raw pointers."""
    if type(raw) is not bytes or not isinstance(layout, NativeCompositeLayout):
        raise NativeCompositeDecodeError("Expected immutable bytes and a composite layout")
    native_type = layout.ctypes_type()
    if len(raw) != ctypes.sizeof(native_type):
        raise NativeCompositeDecodeError("Native buffer size does not match layout")
    selections = union_members if union_members is not None else {}
    if not isinstance(selections, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in selections.items()):
        raise NativeCompositeDecodeError("Union selections must map paths to member names")
    used: set[str] = set()

    def decode(value: object, specification: object, path: str) -> object:
        if isinstance(specification, str):
            return value
        if isinstance(specification, NativeArrayType):
            return tuple(decode(value[index], specification.element, f"{path}[{index}]") for index in range(specification.count))
        if isinstance(specification, NativeCompositeLayout):
            if specification.kind == "union":
                member = selections.get(path)
                allowed = dict(specification.fields)
                if member not in allowed:
                    raise NativeCompositeDecodeError(f"Explicit union member required at {path}")
                used.add(path)
                return {member: decode(getattr(value, member), allowed[member], f"{path}.{member}")}
            return {name: decode(getattr(value, name), field_type, f"{path}.{name}") for name, field_type in specification.fields}
        raise NativeCompositeDecodeError("Unsupported ABI field type")

    instance = native_type.from_buffer_copy(raw)
    result = decode(instance, layout, layout.name)
    if set(selections) != used:
        raise NativeCompositeDecodeError("Unknown or unused union selection path")
    return result
