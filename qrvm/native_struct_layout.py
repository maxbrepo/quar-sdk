"""Explicit C struct layout descriptors for the experimental native ABI.

This module verifies memory layouts; it does not expose arbitrary native
memory access or enable struct arguments in Visual Quar source code.
"""

from __future__ import annotations

import ctypes
from functools import lru_cache
from dataclasses import dataclass


class NativeStructLayoutError(ValueError):
    """Report an unsupported or ambiguous C structure declaration."""


_FIELD_TYPES = {
    "i32": ctypes.c_int32,
    "u32": ctypes.c_uint32,
    "i64": ctypes.c_int64,
    "u64": ctypes.c_uint64,
    "f32": ctypes.c_float,
    "f64": ctypes.c_double,
}


@dataclass(frozen=True)
class NativeStructLayout:
    """Describe a C struct using ordered, explicitly typed scalar fields."""

    name: str
    fields: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.isascii() or not self.name.isidentifier():
            raise NativeStructLayoutError("Struct name must be an ASCII identifier")
        if not isinstance(self.fields, tuple) or not self.fields:
            raise NativeStructLayoutError("Struct requires a nonempty tuple of fields")
        names: set[str] = set()
        for field in self.fields:
            if not isinstance(field, tuple) or len(field) != 2:
                raise NativeStructLayoutError("Each field must be a (name, type) pair")
            field_name, kind = field
            if not isinstance(field_name, str) or not field_name.isascii() or not field_name.isidentifier():
                raise NativeStructLayoutError("Field name must be an ASCII identifier")
            if field_name in names:
                raise NativeStructLayoutError("Duplicate struct field")
            if kind not in _FIELD_TYPES:
                raise NativeStructLayoutError("Unsupported struct field type")
            names.add(field_name)

    @lru_cache(maxsize=256)
    def ctypes_type(self) -> type[ctypes.Structure]:
        """Produce a naturally aligned ctypes.Structure class for ABI checks."""
        return type(self.name, (ctypes.Structure,), {
            "_fields_": [(name, _FIELD_TYPES[kind]) for name, kind in self.fields]
        })

    def describe(self) -> dict[str, object]:
        """Return size, alignment and field offsets for comparison with C."""
        structure = self.ctypes_type()
        return {
            "size": ctypes.sizeof(structure),
            "alignment": ctypes.alignment(structure),
            "offsets": {name: getattr(structure, name).offset for name, _ in self.fields},
        }
