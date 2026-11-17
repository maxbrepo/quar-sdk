"""Experimental immutable callable signatures for Chapter 5."""
from dataclasses import dataclass


@dataclass(frozen=True)
class FunctionSignature:
    """Describe callable parameter and return types without runtime values."""
    parameter_types: tuple[str, ...]
    return_type: str

    def is_compatible_with(self, other: "FunctionSignature") -> bool:
        """Return True for exactly matching parameter and return types."""
        return isinstance(other, FunctionSignature) and self == other
