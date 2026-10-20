"""Execution frame metadata for the Python QVM bootstrap.

Frames describe execution contexts; the existing operand stack remains shared.
"""
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CallFrame:
    """An active invocation or scoped execution context.

    locals refers to the live variable environment of that invocation.
    stack_base records operand stack depth on entry; it is diagnostic only.
    """

    name: str
    locals: dict[str, Any]
    stack_base: int
    scoped: bool = False


def describe_frames(frames: list[CallFrame]) -> tuple[str, ...]:
    """Return an immutable outermost-to-innermost call trace."""
    return tuple(frame.name for frame in frames)
