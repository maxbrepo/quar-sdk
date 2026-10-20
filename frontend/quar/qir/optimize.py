"""Conservative QIR phi simplification, preserving SSA control-flow semantics."""
from __future__ import annotations
from dataclasses import replace
from .model import QBranch, QFunction, QReturn, QValue
from .validation import validate_function


def simplify_phis(function: QFunction) -> QFunction:
    """Return a new function with provably redundant phi nodes removed.

    A phi is redundant when every incoming value is identical, ignoring
    references to its own result. Phi cycles with no external value remain.
    No arithmetic or side-effecting instruction is removed.
    """
    validate_function(function)
    aliases: dict[str, QValue] = {}

    def resolve(value: QValue) -> QValue:
        seen: set[str] = set()
        while value.name in aliases:
            if value.name in seen:
                raise ValueError("Cyclic phi substitution")
            seen.add(value.name)
            value = aliases[value.name]
        return value

    # Iterate because simplifying one phi can make another phi redundant.
    while True:
        changed = False
        for block in function.blocks:
            for phi in block.phis:
                if phi.result.name in aliases:
                    continue
                incoming = [resolve(value) for _, value in phi.incoming]
                external = [value for value in incoming if value.name != phi.result.name]
                if external and all(value == external[0] for value in external):
                    replacement = external[0]
                    if replacement.type != phi.result.type:
                        continue
                    aliases[phi.result.name] = replacement
                    changed = True
        if not changed:
            break

    if not aliases:
        return function
    rewritten = []
    for block in function.blocks:
        phis = tuple(replace(phi, incoming=tuple((label, resolve(value)) for label, value in phi.incoming))
                     for phi in block.phis if phi.result.name not in aliases)
        instructions = tuple(replace(instr, operands=tuple(resolve(value) for value in instr.operands))
                             for instr in block.instructions)
        terminator = block.terminator
        if isinstance(terminator, QBranch):
            terminator = replace(terminator, condition=resolve(terminator.condition))
        elif isinstance(terminator, QReturn) and terminator.value is not None:
            terminator = replace(terminator, value=resolve(terminator.value))
        rewritten.append(replace(block, phis=phis, instructions=instructions, terminator=terminator))
    result = replace(function, blocks=tuple(rewritten))
    validate_function(result)
    return result
