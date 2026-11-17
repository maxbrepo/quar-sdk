"""Explicit, naturally aligned C union layouts for native ABI validation.

Union descriptors do not select an active member or grant raw memory access.
"""

from __future__ import annotations

import ctypes
from dataclasses import dataclass
from functools import lru_cache

from qrvm.native_struct_layout import NativeStructLayoutError, _FIELD_TYPES


@dataclass(frozen=True)
class NativeUnionLayout:
    """Describe a C union of named scalar fields, without active-member tracking."""

    name: str
    fields: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.isascii() or not self.name.isidentifier():
            raise NativeStructLayoutError("Union name must be an ASCII identifier")
        if not isinstance(self.fields, tuple) or not self.fields:
            raise NativeStructLayoutError("Union requires a nonempty tuple of fields")
        seen: set[str] = set()
        for field in self.fields:
            if not isinstance(field, tuple) or len(field) != 2:
                raise NativeStructLayoutError("Each union field must be a (name, type) pair")
            field_name, kind = field
            if not isinstance(field_name, str) or not field_name.isascii() or not field_name.isidentifier():
                raise NativeStructLayoutError("Union field name must be an ASCII identifier")
            if field_name in seen:
                raise NativeStructLayoutError("Duplicate union field")
            if not isinstance(kind, str) or kind not in _FIELD_TYPES:
                raise NativeStructLayoutError("Unsupported union field type")
            seen.add(field_name)

    @lru_cache(maxsize=256)
    def ctypes_type(self) -> type[ctypes.Union]:
        """Create a native union type using the host platform's C ABI."""
        return type(self.name, (ctypes.Union,), {
            "_fields_": [(name, _FIELD_TYPES[kind]) for name, kind in self.fields]
        })

    def describe(self) -> dict[str, object]:
        """Return native size, alignment and offsets (all union offsets are zero)."""
        union = self.ctypes_type()
        return {
            "size": ctypes.sizeof(union),
            "alignment": ctypes.alignment(union),
            "offsets": {name: getattr(union, name).offset for name, _ in self.fields},
        }
