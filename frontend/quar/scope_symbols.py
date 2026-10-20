"""Lexical symbol identities for the planned scoped lowering pass.

This registry is independent of semantic analysis and code generation until
those components explicitly integrate it.
"""
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator


class DuplicateBindingError(ValueError):
    """Raised when a name is declared twice in the same lexical scope."""


@dataclass(frozen=True)
class Binding:
    source_name: str
    internal_name: str
    depth: int


class LexicalBindings:
    """Allocate unique IDs and resolve the nearest visible declaration."""

    def __init__(self) -> None:
        self._frames: list[dict[str, Binding]] = [{}]
        self._next_id = 0

    @property
    def depth(self) -> int:
        """Return the current lexical nesting depth (root is zero)."""
        return len(self._frames) - 1

    def enter(self) -> None:
        """Push an empty lexical scope."""
        self._frames.append({})

    def leave(self) -> None:
        """Pop the current scope without permitting removal of the root."""
        if len(self._frames) == 1:
            raise ValueError("Cannot leave the root scope")
        self._frames.pop()

    @contextmanager
    def scoped(self) -> Iterator["LexicalBindings"]:
        """Open a scope and restore it even when processing raises an error."""
        self.enter()
        try:
            yield self
        finally:
            self.leave()

    def declare(self, name: str) -> Binding:
        """Create a new binding, rejecting duplicates in the current frame."""
        frame = self._frames[-1]
        if name in frame:
            raise DuplicateBindingError(
                f"Variable '{name}' is already declared in this scope"
            )
        self._next_id += 1
        binding = Binding(name, f"__vq_binding_{self._next_id}", self.depth)
        frame[name] = binding
        return binding

    def resolve_current(self, name: str) -> Binding | None:
        """Find a declaration in the current scope only."""
        return self._frames[-1].get(name)

    def resolve(self, name: str) -> Binding | None:
        """Find the nearest visible declaration, or return None."""
        for frame in reversed(self._frames):
            if name in frame:
                return frame[name]
        return None

    def resolve_required(self, name: str) -> Binding:
        """Return the nearest visible binding or reject an unknown name."""
        binding = self.resolve(name)
        if binding is None:
            raise NameError(f"Variable '{name}' is not declared")
        return binding

    def is_declared_here(self, name: str) -> bool:
        """Report whether the current frame declares a name."""
        return self.resolve_current(name) is not None

    @contextmanager
    def function_scoped(self) -> Iterator["LexicalBindings"]:
        """Create an isolated function namespace without resetting binding IDs.

        Function parameters and locals must not resolve names from an unrelated
        function. The original scope stack is restored on normal or error exit.
        """
        previous_frames = self._frames
        self._frames = [{}]
        try:
            yield self
        finally:
            self._frames = previous_frames

    def visible_bindings(self) -> dict[str, Binding]:
        """Return a snapshot of the nearest binding for each visible name."""
        visible: dict[str, Binding] = {}
        for frame in self._frames:
            visible.update(frame)
        return visible
