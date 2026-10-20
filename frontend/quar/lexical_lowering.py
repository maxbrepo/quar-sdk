"""Backend-neutral lexical name planning without mutating source AST nodes.

The plan is deliberately opt-in: backends must explicitly consume the result
before shadowing can be enabled in the semantic frontend.
"""
from dataclasses import dataclass

from .scope_symbols import LexicalBindings, Binding


@dataclass(frozen=True)
class NameResolution:
    """Resolved storage name and whether a declaration was introduced."""
    storage_name: str
    introduced: bool


class LexicalNamePlanner:
    """Plan stable storage identities for explicit and inferred variables."""

    def __init__(self) -> None:
        self.bindings = LexicalBindings()

    def enter(self) -> None:
        self.bindings.enter()

    def leave(self) -> None:
        self.bindings.leave()

    def declare(self, name: str) -> NameResolution:
        binding = self.bindings.declare(name)
        return NameResolution(binding.internal_name, True)

    def assign(self, name: str, allow_inference: bool = False) -> NameResolution:
        binding = self.bindings.resolve(name)
        if binding is None:
            if not allow_inference:
                raise NameError(f"Variable '{name}' is not declared")
            return self.declare(name)
        return NameResolution(binding.internal_name, False)

    def read(self, name: str) -> str:
        return self.bindings.resolve_required(name).internal_name
