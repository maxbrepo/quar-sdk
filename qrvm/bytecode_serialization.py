"""Portable, deterministic QBC v1 envelope for bootstrap QRVM programs.

QBC is a language-level interchange format, not Python pickle or machine code.
"""
import hashlib
import json
import struct
from pathlib import Path
from typing import Any

from .bytecode_format import BytecodeHeader, validate_bytecode_package, BytecodeFormatError
from .bytecode_loader import load_bytecode, LoadedBytecode
from .instructions import OpCode

QBC_MAGIC = b"QBC\x00"
QBC_MAJOR = 1
QBC_MINOR = 0
MAX_PAYLOAD_BYTES = 32 * 1024 * 1024


class QBCError(ValueError):
    """Malformed, unsupported or oversized portable bytecode."""


def _encode(value: Any, depth: int = 0) -> Any:
    if depth > 100:
        raise QBCError("bytecode nesting limit exceeded")
    if value is None or type(value) in (bool, int, str):
        return value
    if type(value) is float:
        return {"@": "float", "v": value.hex()}
    if isinstance(value, OpCode):
        return {"@": "opcode", "v": value.name}
    if isinstance(value, BytecodeHeader):
        return {"@": "header", "v": [value.magic, value.major, value.minor]}
    if type(value) is tuple:
        return {"@": "tuple", "v": [_encode(item, depth + 1) for item in value]}
    if type(value) is list:
        return [_encode(item, depth + 1) for item in value]
    if type(value) is dict:
        entries = [[_encode(k, depth + 1), _encode(v, depth + 1)] for k, v in value.items()]
        entries.sort(key=lambda item: json.dumps(item[0], sort_keys=True, ensure_ascii=True))
        return {"@": "dict", "v": entries}
    raise QBCError(f"unsupported bytecode value type: {type(value).__name__}")


def _decode(value: Any, depth: int = 0) -> Any:
    if depth > 100:
        raise QBCError("bytecode nesting limit exceeded")
    if value is None or type(value) in (bool, int, str):
        return value
    if type(value) is list:
        return [_decode(item, depth + 1) for item in value]
    if type(value) is not dict or set(value) != {"@", "v"}:
        raise QBCError("invalid tagged bytecode value")
    tag, raw = value["@"], value["v"]
    if tag == "float" and type(raw) is str:
        try:
            return float.fromhex(raw)
        except ValueError as exc:
            raise QBCError("invalid float encoding") from exc
    if tag == "opcode" and type(raw) is str:
        try:
            return OpCode[raw]
        except KeyError as exc:
            raise QBCError("unknown bytecode opcode") from exc
    if tag == "header" and type(raw) is list and len(raw) == 3:
        if type(raw[0]) is str and type(raw[1]) is int and type(raw[2]) is int:
            return BytecodeHeader(*raw)
    if tag == "tuple" and type(raw) is list:
        return tuple(_decode(item, depth + 1) for item in raw)
    if tag == "dict" and type(raw) is list:
        result = {}
        for pair in raw:
            if type(pair) is not list or len(pair) != 2:
                raise QBCError("invalid dictionary entry")
            key, item = (_decode(part, depth + 1) for part in pair)
            try:
                if key in result:
                    raise QBCError("duplicate dictionary key")
                result[key] = item
            except TypeError as exc:
                raise QBCError("unhashable dictionary key") from exc
        return result
    raise QBCError("unknown or invalid bytecode value tag")


def dumps_qbc(program: Any, *, verify: bool = False) -> bytes:
    """Serialize a versioned QRVM package as a deterministic QBC artifact."""
    try:
        loaded = load_bytecode(program, verify=verify)
        payload = json.dumps(_encode(loaded.package), ensure_ascii=True,
                             sort_keys=True, separators=(",", ":"), allow_nan=False).encode("ascii")
        if len(payload) > MAX_PAYLOAD_BYTES:
            raise QBCError("QBC payload too large")
        return (QBC_MAGIC + bytes((QBC_MAJOR, QBC_MINOR)) +
                struct.pack(">I", len(payload)) + hashlib.sha256(payload).digest() + payload)
    except (BytecodeFormatError, ValueError, TypeError, RecursionError) as exc:
        if isinstance(exc, QBCError):
            raise
        raise QBCError(f"cannot serialize QBC: {exc}") from exc


def loads_qbc(data: bytes, *, verify: bool = True) -> LoadedBytecode:
    """Read a QBC artifact, check integrity and load a detached program snapshot."""
    if type(data) is not bytes or len(data) < 42 or data[:4] != QBC_MAGIC:
        raise QBCError("invalid QBC header")
    if data[4] != QBC_MAJOR or data[5] > QBC_MINOR:
        raise QBCError("unsupported QBC version")
    length = struct.unpack(">I", data[6:10])[0]
    if length > MAX_PAYLOAD_BYTES or len(data) != 42 + length:
        raise QBCError("invalid QBC payload length")
    payload = data[42:]
    if hashlib.sha256(payload).digest() != data[10:42]:
        raise QBCError("QBC payload checksum mismatch")
    try:
        package = _decode(json.loads(payload.decode("ascii")))
        return load_bytecode(package, verify=verify)
    except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
        raise QBCError(f"invalid QBC payload: {exc}") from exc


def write_qbc(path: str | Path, program: Any, *, verify: bool = False) -> None:
    """Write QBC bytes to disk; returns None."""
    Path(path).write_bytes(dumps_qbc(program, verify=verify))


def read_qbc(path: str | Path, *, verify: bool = True) -> LoadedBytecode:
    """Load QBC from disk; returns a validated LoadedBytecode."""
    path = Path(path)
    if path.stat().st_size > MAX_PAYLOAD_BYTES + 42:
        raise QBCError("QBC file too large")
    return loads_qbc(path.read_bytes(), verify=verify)
