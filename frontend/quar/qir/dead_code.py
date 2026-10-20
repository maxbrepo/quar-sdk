"""Conservative dead-result elimination for validated SSA-like QIR."""
from __future__ import annotations
from dataclasses import replace
from .model import QBranch, QFunction, QReturn
from .validation import validate_function

# Only these opcodes are proven non-trapping and side-effect free here.
# Arithmetic can overflow; load can fail; cast can narrow; store mutates memory.
_REMOVABLE = frozenset({"const", "copy"})


def eliminate_dead_results(function: QFunction) -> QFunction:
    """Remove unused const/copy definitions without altering observable effects.

    Iterate to a fixed point so dead chains disappear. Keep all phi nodes:
    their edge semantics and loop-carried dependencies require separate work.
    Return a new function and preserve the original immutable graph.
    """
    validate_function(function)
    current = function
    while True:
        used: set[str] = set()
        for block in current.blocks:
            for phi in block.phis:
                used.update(value.name for _, value in phi.incoming)
            for instruction in block.instructions:
                used.update(value.name for value in instruction.operands)
            term = block.terminator
            if isinstance(term, QBranch):
                used.add(term.condition.name)
            elif isinstance(term, QReturn) and term.value is not None:
                used.add(term.value.name)
        changed = False
        blocks = []
        for block in current.blocks:
            instructions = []
            for instruction in block.instructions:
                if (instruction.opcode in _REMOVABLE and
                        instruction.result is not None and
                        instruction.result.name not in used):
                    changed = True
                    continue
                instructions.append(instruction)
            blocks.append(replace(block, instructions=tuple(instructions)))
        if not changed:
            validate_function(current)
            return current
        current = replace(current, blocks=tuple(blocks))
