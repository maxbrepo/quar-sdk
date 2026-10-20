"""Experimental optional type rules for Visual Quar Chapter 15.6.

This is a typed semantic prototype, not yet connected to the .vq parser.
"""
from dataclasses import dataclass
from enum import Enum, auto


class OptionalTypeError(TypeError):
    """An optional value is used in a type-unsafe way."""


@dataclass(frozen=True)
class ValueType:
    name: str
    optional: bool = False

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("Type name must not be empty")

    def as_optional(self) -> "ValueType":
        """Return the nullable counterpart of this type."""
        return ValueType(self.name, True)


class Presence(Enum):
    UNKNOWN = auto()
    PRESENT = auto()
    ABSENT = auto()


@dataclass(frozen=True)
class FlowValue:
    type: ValueType
    presence: Presence = Presence.UNKNOWN

    def __post_init__(self) -> None:
        if not self.type.optional and self.presence == Presence.ABSENT:
            raise OptionalTypeError("A non-optional value cannot be absent")

    def checked_present(self) -> "FlowValue":
        """Return a flow-refined value after a successful presence check."""
        if self.presence == Presence.ABSENT:
            raise OptionalTypeError("Value is known to be absent")
        return FlowValue(self.type, Presence.PRESENT)

    def checked_absent(self) -> "FlowValue":
        """Return a flow-refined value for the absence branch."""
        if not self.type.optional or self.presence == Presence.PRESENT:
            raise OptionalTypeError("Value cannot be absent on this path")
        return FlowValue(self.type, Presence.ABSENT)

    def read(self) -> ValueType:
        """Return the safe non-optional type, or reject an unchecked read."""
        if self.type.optional and self.presence != Presence.PRESENT:
            raise OptionalTypeError("Optional value requires a presence check")
        return ValueType(self.type.name)


def can_assign(source: ValueType, destination: ValueType) -> bool:
    """Check optionality only; numeric conversion rules belong to the frontend."""
    return source.name == destination.name and (destination.optional or not source.optional)


def join_presence(left: Presence, right: Presence) -> Presence:
    """Merge branch states conservatively at a control-flow join."""
    return left if left == right else Presence.UNKNOWN
