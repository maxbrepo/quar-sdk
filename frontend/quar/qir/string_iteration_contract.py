"""Explicit UTF-8 iteration contract; not yet an executable QIR operation.

Byte offsets, Unicode scalar values and grapheme clusters are distinct units.
This module deliberately exposes only scalar-value traversal for now.
"""
from __future__ import annotations

from dataclasses import dataclass


class QStringIterationError(ValueError):
    """Reject malformed text or ambiguous string indexing."""


@dataclass(frozen=True)
class QStringScalar:
    """One Unicode scalar value and its half-open UTF-8 byte span."""

    value: int
    byte_start: int
    byte_end: int


def utf8_scalars(value: str) -> tuple[QStringScalar, ...]:
    """Return Unicode scalar values with byte offsets; reject surrogate code points."""
    if not isinstance(value, str):
        raise QStringIterationError("Expected Unicode text")
    result: list[QStringScalar] = []
    offset = 0
    for character in value:
        scalar = ord(character)
        if 0xD800 <= scalar <= 0xDFFF:
            raise QStringIterationError("Unpaired Unicode surrogate is not a scalar value")
        size = len(character.encode("utf-8"))
        result.append(QStringScalar(scalar, offset, offset + size))
        offset += size
    return tuple(result)


@dataclass(frozen=True)
class QStringUTF8:
    """Immutable, length-delimited UTF-8 storage; no NUL terminator is assumed."""

    data: bytes
    byte_length: int


def encode_utf8(value: str) -> QStringUTF8:
    """Encode valid Unicode scalar text into a length-delimited byte buffer."""
    utf8_scalars(value)  # Reject surrogate code points before encoding.
    data = value.encode("utf-8")
    return QStringUTF8(data, len(data))


def decode_utf8(storage: QStringUTF8) -> tuple[QStringScalar, ...]:
    """Validate UTF-8 storage and return scalar values with byte spans."""
    if (not isinstance(storage, QStringUTF8) or
            type(storage.data) is not bytes or
            type(storage.byte_length) is not int or
            storage.byte_length != len(storage.data)):
        raise QStringIterationError("Invalid UTF-8 buffer length or storage")
    try:
        value = storage.data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise QStringIterationError("Invalid UTF-8 encoding") from exc
    return utf8_scalars(value)
