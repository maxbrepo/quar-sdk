"""Experimental bridge between Visual Quar AST and optional-type flow rules.

No .vq syntax is introduced here; optional declarations are supplied as metadata.
"""
from dataclasses import dataclass, field
from frontend.quar.ast_nodes import Assignment, Variable, VariableDeclaration
from memory.optional_types import FlowValue, OptionalTypeError, Presence, ValueType, can_assign, join_presence


@dataclass
class OptionalFlowAnalyzer:
    """Track optional presence for a sequence of existing Quar AST statements."""
    values: dict[str, FlowValue] = field(default_factory=dict)

    def declare(self, node: VariableDeclaration, *, optional: bool = False,
                presence: Presence = Presence.UNKNOWN) -> None:
        """Declare an AST variable with explicit experimental optional metadata."""
        if node.name in self.values:
            raise OptionalTypeError(f"Variable already declared: {node.name}")
        self.values[node.name] = FlowValue(ValueType(node.var_type, optional), presence)

    def read(self, node: Variable) -> ValueType:
        """Validate a variable read and return its safe value type."""
        if node.name not in self.values:
            raise OptionalTypeError(f"Unknown variable: {node.name}")
        return self.values[node.name].read()

    def refine_present(self, name: str) -> None:
        """Record a proven presence check on the current control-flow path."""
        self.values[name] = self.values[name].checked_present()

    def refine_absent(self, name: str) -> None:
        """Record a proven absence check on the current control-flow path."""
        self.values[name] = self.values[name].checked_absent()

    def assign(self, node: Assignment, source: ValueType,
               presence: Presence = Presence.UNKNOWN) -> None:
        """Check optionality and invalidate stale presence facts after assignment."""
        if node.name not in self.values:
            raise OptionalTypeError(f"Unknown variable: {node.name}")
        destination = self.values[node.name].type
        if not can_assign(source, destination):
            raise OptionalTypeError(f"Cannot assign {source} to {destination}")
        self.values[node.name] = FlowValue(destination, (Presence.PRESENT if not source.optional else presence))

    def fork(self) -> "OptionalFlowAnalyzer":
        """Copy flow facts before analyzing an independent branch."""
        return OptionalFlowAnalyzer(self.values.copy())

    def merge(self, other: "OptionalFlowAnalyzer") -> None:
        """Keep only facts guaranteed by both control-flow branches."""
        if self.values.keys() != other.values.keys():
            raise OptionalTypeError("Cannot merge incompatible variable scopes")
        for name, left in list(self.values.items()):
            right = other.values[name]
            if left.type != right.type:
                raise OptionalTypeError(f"Conflicting branch types: {name}")
            self.values[name] = FlowValue(left.type, join_presence(left.presence, right.presence))
