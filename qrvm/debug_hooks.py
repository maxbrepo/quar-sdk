"""Opt-in, read-only instruction observation for the Python QVM bootstrap."""
from dataclasses import dataclass
from typing import Callable

from .call_frames import CallFrame, describe_frames


@dataclass(frozen=True)
class DebugEvent:
    """A snapshot of execution metadata, not a mutable VM state reference."""

    phase: str
    instruction_index: int
    opcode: str
    frame_names: tuple[str, ...]
    stack_depth: int
    error_type: str | None = None
    error_message: str | None = None


def make_event(phase: str, index: int, opcode: object,
               frames: list[CallFrame], stack_depth: int,
               error: Exception | None = None) -> DebugEvent:
    """Create a snapshot; return an immutable event."""
    return DebugEvent(
        phase=phase,
        instruction_index=index,
        opcode=getattr(opcode, 'name', str(opcode)),
        frame_names=describe_frames(frames),
        stack_depth=stack_depth,
        error_type=type(error).__name__ if error is not None else None,
        error_message=str(error) if error is not None else None,
    )


DebugHook = Callable[[DebugEvent], None]
