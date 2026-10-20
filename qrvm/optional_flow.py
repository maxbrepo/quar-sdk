"""Conservative, immutable optional-presence dataflow facts.

This is a reusable foundation, not a complete control-flow graph solver.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Mapping


class Presence(Enum):
    UNKNOWN = "unknown"
    PRESENT = "present"
    ABSENT = "absent"


@dataclass(frozen=True)
class FlowState:
    """Facts guaranteed at one program point, indexed by variable name."""
    facts: tuple[tuple[str, Presence], ...] = ()

    @classmethod
    def from_mapping(cls, facts: Mapping[str, Presence]) -> "FlowState":
        return cls(tuple(sorted(facts.items())))

    def get(self, name: str) -> Presence:
        return dict(self.facts).get(name, Presence.UNKNOWN)

    def set(self, name: str, presence: Presence) -> "FlowState":
        updated = dict(self.facts)
        updated[name] = presence
        return self.from_mapping(updated)

    def invalidate(self, names) -> "FlowState":
        updated = dict(self.facts)
        for name in names:
            updated[name] = Presence.UNKNOWN
        return self.from_mapping(updated)

    def join(self, other: "FlowState") -> "FlowState":
        """Keep a fact only if every incoming path guarantees it."""
        names = dict(self.facts).keys() | dict(other.facts).keys()
        return self.from_mapping({
            name: self.get(name) if self.get(name) == other.get(name) else Presence.UNKNOWN
            for name in names
        })

    def refine(self, assumptions: Mapping[str, Presence]) -> "FlowState":
        """Apply facts established by a proven branch condition."""
        updated = dict(self.facts)
        updated.update(assumptions)
        return self.from_mapping(updated)
