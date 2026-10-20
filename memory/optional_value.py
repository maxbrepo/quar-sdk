"""Experimental tagged optional-value model for Chapter 15.5.

This module is a reference model, not the Visual Quar language implementation.
"""

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


class EmptyOptionalError(ValueError):
    """Raised when an absent optional value is unwrapped."""


@dataclass(frozen=True)
class OptionalValue(Generic[T]):
    present: bool
    value: T | None = None

    def __post_init__(self) -> None:
        if not self.present and self.value is not None:
            raise ValueError("An absent optional cannot carry a value")
        if self.present and self.value is None:
            raise ValueError("A present optional must carry a non-null value")

    @classmethod
    def some(cls, value: T) -> "OptionalValue[T]":
        """Wrap a non-null value; return a present optional."""
        return cls(present=True, value=value)

    @classmethod
    def empty(cls) -> "OptionalValue[T]":
        """Create an absent optional value."""
        return cls(present=False)

    def unwrap(self) -> T:
        """Return the stored value or raise EmptyOptionalError."""
        if not self.present:
            raise EmptyOptionalError("Cannot unwrap an absent optional value")
        assert self.value is not None
        return self.value
