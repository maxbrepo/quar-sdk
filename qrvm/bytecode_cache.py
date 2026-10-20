"""Content-addressed QBC cache keys; compilation remains the caller's job."""
import hashlib
import json
from pathlib import Path
from typing import Mapping

from .bytecode_serialization import read_qbc, write_qbc, QBCError


def cache_key(source: bytes, *, compiler_id: str, dependencies: Mapping[str, bytes] | None = None) -> str:
    """Return a stable digest of source, compiler identity and dependency contents."""
    if type(source) is not bytes or not compiler_id:
        raise ValueError("source bytes and compiler_id are required")
    digest = hashlib.sha256()
    parts = {"compiler": compiler_id, "dependencies": {
        name: hashlib.sha256(data).hexdigest()
        for name, data in (dependencies or {}).items()
    }}
    metadata = json.dumps(parts, sort_keys=True, separators=(",", ":")).encode("utf-8")
    for item in (metadata, source):
        digest.update(len(item).to_bytes(8, "big"))
        digest.update(item)
    return digest.hexdigest()


def cache_path(directory: str | Path, key: str) -> Path:
    """Return the QBC cache file path for a validated hexadecimal key."""
    if len(key) != 64 or any(c not in "0123456789abcdef" for c in key):
        raise ValueError("invalid cache key")
    return Path(directory) / f"{key}.qbc"
