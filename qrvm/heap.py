"""Bootstrap heap accounting for QRVM composite values.

The registry observes legacy dictionary objects without replacing their identity.
Ownership, collection, and byte-accurate allocation are deliberately out of scope.
"""
from dataclasses import dataclass
from typing import Any


class HeapError(RuntimeError):
    """Raised when a heap handle is invalid or the registry limit is exceeded."""


@dataclass(frozen=True)
class HeapEntry:
    handle: int
    kind: str
    value: Any


class BootstrapHeap:
    """Run-scoped, identity-preserving registry of VM-managed composites."""

    def __init__(self, max_objects: int | None = None) -> None:
        if max_objects is not None and (type(max_objects) is not int or max_objects < 0):
            raise ValueError("max_objects must be a nonnegative integer or None")
        self.max_objects = max_objects
        self._entries: dict[int, HeapEntry] = {}
        self._next_handle = 1

    def register(self, kind: str, value: Any) -> int:
        if kind not in ("array", "object"):
            raise HeapError(f"Unsupported heap kind: {kind!r}")
        if not isinstance(value, dict):
            raise HeapError("Heap composite must be a dictionary")
        if kind == "array" and "__array__" not in value:
            raise HeapError("Array heap object has no array storage")
        if kind == "object" and "__fields__" not in value:
            raise HeapError("Object heap entry has no fields")
        if self.max_objects is not None and len(self._entries) >= self.max_objects:
            raise HeapError("Heap object limit exceeded")
        handle = self._next_handle
        self._next_handle += 1
        self._entries[handle] = HeapEntry(handle, kind, value)
        return handle

    def get(self, handle: int) -> HeapEntry:
        if type(handle) is not int or handle not in self._entries:
            raise HeapError(f"Unknown heap handle: {handle!r}")
        return self._entries[handle]

    @property
    def object_count(self) -> int:
        return len(self._entries)

    def reset(self) -> None:
        self._entries.clear()
        self._next_handle = 1

    def snapshot(self) -> tuple[tuple[int, str], ...]:
        """Return immutable allocation metadata, without exposing mutable payloads."""
        return tuple((entry.handle, entry.kind) for entry in self._entries.values())
