"""Optional, low-overhead instruction counters and inclusive timings for QVM."""
from dataclasses import dataclass
from time import perf_counter_ns


@dataclass(frozen=True)
class ProfileEntry:
    instructions: int
    elapsed_ns: int


@dataclass(frozen=True)
class ProfileSnapshot:
    total: ProfileEntry
    by_opcode: dict[str, ProfileEntry]
    by_function: dict[str, ProfileEntry]


class InstructionProfiler:
    """Accumulate per-instruction measurements; snapshots detach mutable state."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._opcode: dict[str, list[int]] = {}
        self._function: dict[str, list[int]] = {}
        self._total = [0, 0]

    def start(self) -> int:
        """Return a monotonic timestamp for an instruction."""
        return perf_counter_ns()

    def record(self, opcode: object, function: str, started_ns: int) -> None:
        """Record inclusive elapsed time, including nested function execution."""
        elapsed = max(0, perf_counter_ns() - started_ns)
        name = getattr(opcode, 'name', str(opcode))
        for bucket, key in ((self._opcode, name), (self._function, function)):
            entry = bucket.setdefault(key, [0, 0])
            entry[0] += 1
            entry[1] += elapsed
        self._total[0] += 1
        self._total[1] += elapsed

    def snapshot(self) -> ProfileSnapshot:
        """Return an immutable summary of the current counters."""
        return ProfileSnapshot(
            ProfileEntry(*self._total),
            {key: ProfileEntry(*value) for key, value in self._opcode.items()},
            {key: ProfileEntry(*value) for key, value in self._function.items()},
        )
