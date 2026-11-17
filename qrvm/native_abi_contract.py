"""Validate an external C ABI probe before constructing opaque output storage.

A storage descriptor is only safe for a trusted C function whose signature is
`int32_t function(T *out)` and whose C definition matches the probed T.
This module neither guesses a third-party layout nor decodes C unions.
"""
from __future__ import annotations

from dataclasses import dataclass

from qrvm.native_composite_layout import NativeArrayType, NativeCompositeLayout


class NativeABIContractError(ValueError):
    """An unverified or incompatible native output layout was requested."""


@dataclass(frozen=True)
class NativeOutputABIContract:
    """Dimensions from a compiled C probe, not from guessed constants."""

    size: int
    alignment: int
    offsets: tuple[tuple[str, int], ...]

    def __post_init__(self) -> None:
        if type(self.size) is not int or not 1 <= self.size <= 1024 * 1024:
            raise NativeABIContractError("Invalid probed C object size")
        if (type(self.alignment) is not int or self.alignment not in (4, 8)
                or self.size % self.alignment):
            raise NativeABIContractError("Unsupported C object alignment")
        if not isinstance(self.offsets, tuple):
            raise NativeABIContractError("C field offsets must be a tuple")
        seen = set()
        for name, offset in self.offsets:
            if (type(name) is not str or not name.isascii() or not name.isidentifier()
                    or name in seen or type(offset) is not int or not 0 <= offset < self.size):
                raise NativeABIContractError("Invalid or duplicate C field offset")
            seen.add(name)

    def opaque_storage(self, name: str) -> NativeCompositeLayout:
        """Return exact-size/alignment storage; fields are intentionally opaque."""
        scalar = 'u64' if self.alignment == 8 else 'u32'
        words = self.size // self.alignment
        if words > 65536:
            raise NativeABIContractError("Storage requires too many array elements")
        layout = NativeCompositeLayout(name, 'struct', (
            ('storage', NativeArrayType(scalar, words)),
        ))
        dimensions = layout.describe()
        if dimensions['size'] != self.size or dimensions['alignment'] != self.alignment:
            raise NativeABIContractError("Host ABI storage does not match the C probe")
        return layout

    def read_i32(self, raw: bytes, field: str) -> int:
        """Read a signed 32-bit value at a compiler-verified field offset."""
        value = self.read_u32(raw, field)
        return value - (1 << 32) if value >= (1 << 31) else value

    def read_u32(self, raw: bytes, field: str) -> int:
        """Read a verified uint32_t field from an immutable output copy."""
        if type(raw) is not bytes or len(raw) != self.size:
            raise NativeABIContractError("Output buffer does not match probed C size")
        try:
            offset = dict(self.offsets)[field]
        except KeyError as exc:
            raise NativeABIContractError("C field has not been verified") from exc
        if offset % 4 or offset + 4 > self.size:
            raise NativeABIContractError("C uint32_t offset is incompatible")
        import sys
        return int.from_bytes(raw[offset:offset + 4], sys.byteorder, signed=False)
