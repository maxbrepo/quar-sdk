"""Structured bootstrap-QVM runtime diagnostics without changing exception semantics."""
from dataclasses import dataclass
from typing import Any

from .call_frames import CallFrame, describe_frames


@dataclass(frozen=True)
class QVMDiagnostic:
    """Snapshot of the deepest failing bytecode instruction and its call chain."""

    category: str
    message: str
    frame_names: tuple[str, ...]
    instruction_index: int
    opcode: str

    def format(self) -> str:
        """Produce a readable message; return a single diagnostic string."""
        chain = " -> ".join(self.frame_names)
        return (f"{self.category}: {self.message}\n"
                f"at {chain}, instruction {self.instruction_index} ({self.opcode})")


def make_diagnostic(error: Exception, frames: list[CallFrame],
                    instruction_index: int, opcode: Any) -> QVMDiagnostic:
    """Capture diagnostic details without retaining mutable frames or locals."""
    name = getattr(opcode, 'name', str(opcode))
    return QVMDiagnostic(type(error).__name__, str(error),
                         describe_frames(frames), instruction_index, name)
