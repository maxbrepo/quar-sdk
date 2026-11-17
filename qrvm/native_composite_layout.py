"""Generic host-C ABI descriptors for nested structs, unions, and fixed arrays.

This experimental layout layer does not authorize pointer dereferencing, union
member access, or automatic mapping into Visual Quar source types.
"""
from __future__ import annotations

import ctypes
from dataclasses import dataclass
from functools import lru_cache

from qrvm.native_struct_layout import NativeStructLayoutError, _FIELD_TYPES


@dataclass(frozen=True)
class NativeArrayType:
    """Describe a fixed-size C array field; produce its ctypes ABI type."""
    element: object
    count: int

    def __post_init__(self) -> None:
        if type(self.count) is not int or not 1 <= self.count <= 65536:
            raise NativeStructLayoutError("Array count must be between 1 and 65536")
        _resolve_type(self.element)

    def ctypes_type(self) -> type:
        return _resolve_type(self.element) * self.count


@dataclass(frozen=True)
class NativeCompositeLayout:
    """Describe a nested C struct or union with natural host ABI alignment."""
    name: str
    kind: str
    fields: tuple[tuple[str, object], ...]

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.isascii() or not self.name.isidentifier():
            raise NativeStructLayoutError("Composite name must be an ASCII identifier")
        if self.kind not in ("struct", "union"):
            raise NativeStructLayoutError("Composite kind must be struct or union")
        if not isinstance(self.fields, tuple) or not self.fields:
            raise NativeStructLayoutError("Composite requires a nonempty tuple of fields")
        names: set[str] = set()
        for field in self.fields:
            if not isinstance(field, tuple) or len(field) != 2:
                raise NativeStructLayoutError("Each field must be a (name, type) pair")
            name, field_type = field
            if not isinstance(name, str) or not name.isascii() or not name.isidentifier() or name in names:
                raise NativeStructLayoutError("Invalid or duplicate composite field")
            _resolve_type(field_type)
            names.add(name)

    @lru_cache(maxsize=256)
    def ctypes_type(self) -> type:
        base = ctypes.Structure if self.kind == "struct" else ctypes.Union
        return type(self.name, (base,), {
            "_fields_": [(name, _resolve_type(field_type)) for name, field_type in self.fields]
        })

    def describe(self) -> dict[str, object]:
        native_type = self.ctypes_type()
        return {
            "size": ctypes.sizeof(native_type),
            "alignment": ctypes.alignment(native_type),
            "offsets": {name: getattr(native_type, name).offset for name, _ in self.fields},
        }


def _resolve_type(specification: object) -> type:
    """Resolve only explicitly permitted ABI descriptors, rejecting raw ctypes."""
    if isinstance(specification, str) and specification in _FIELD_TYPES:
        return _FIELD_TYPES[specification]
    if isinstance(specification, (NativeArrayType, NativeCompositeLayout)):
        return specification.ctypes_type()
    raise NativeStructLayoutError("Unsupported nested native field type")
