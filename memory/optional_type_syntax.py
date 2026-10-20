"""Canonical optional-type spelling for Chapter 15 experiments.

This module is deliberately independent from the production lexer and parser.
"""

from memory.optional_types import ValueType


class OptionalSyntaxError(ValueError):
    """A type spelling is not canonical or is not supported."""


def parse_optional_type(spelling: str) -> ValueType:
    """Parse a canonical T or T? spelling into a ValueType."""
    if not isinstance(spelling, str) or not spelling:
        raise OptionalSyntaxError("Type spelling must be a non-empty string")
    if spelling != spelling.strip():
        raise OptionalSyntaxError("Whitespace around a type is not canonical")
    optional = spelling.endswith("?")
    base = spelling[:-1] if optional else spelling
    if not base or not (base[0].isalpha() or base[0] == "_"):
        raise OptionalSyntaxError("Invalid base type name")
    if not all(char.isalnum() or char == "_" for char in base):
        raise OptionalSyntaxError("Invalid type syntax")
    return ValueType(base, optional)


def format_optional_type(value_type: ValueType) -> str:
    """Return the unique canonical spelling of an experimental ValueType."""
    spelling = value_type.name + ("?" if value_type.optional else "")
    parsed = parse_optional_type(spelling)
    if parsed != value_type:
        raise OptionalSyntaxError("Type cannot be represented canonically")
    return spelling
