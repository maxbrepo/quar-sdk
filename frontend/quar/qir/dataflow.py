"""Conservative must-defined analysis for QIR control-flow graphs."""
from __future__ import annotations

from .model import QBranch, QFunction, QJump, QReturn, QValue


class QIRDataflowError(ValueError):
    """Raised when a reachable instruction uses an undefined QIR value."""


def validate_dataflow(function: QFunction) -> None:
    """Check value definitions on every incoming path, including loop edges.

    This is a name-based, conservative analysis. It does not prove pointer
    initialization, lifetimes, aliasing, or runtime memory safety.
    """
    blocks = {block.label: block for block in function.blocks}
    if not blocks:
        return
    entry = function.blocks[0].label
    successors: dict[str, tuple[str, ...]] = {}
    for block in function.blocks:
        term = block.terminator
        if isinstance(term, QJump):
            successors[block.label] = (term.target,)
        elif isinstance(term, QBranch):
            successors[block.label] = (term.true_target, term.false_target)
        else:
            successors[block.label] = ()

    reachable = {entry}
    pending = [entry]
    while pending:
        current = pending.pop()
        for target in successors[current]:
            if target in blocks and target not in reachable:
                reachable.add(target)
                pending.append(target)

    parameters = {value.name: value.type for value in function.parameters}
    if len(parameters) != len(function.parameters) or any(not name for name in parameters):
        raise QIRDataflowError("Function parameters must have unique nonempty names")

    # A QIR value name has one definition in the function (SSA-like naming).
    definitions = dict(parameters)
    for block in function.blocks:
        for phi in block.phis:
            result = phi.result
            if not result.name or result.name in definitions:
                raise QIRDataflowError(f"Duplicate or empty value definition: {result.name!r}")
            definitions[result.name] = result.type
        for instruction in block.instructions:
            result = instruction.result
            if result is not None:
                if not result.name or result.name in definitions:
                    raise QIRDataflowError(f"Duplicate or empty value definition: {result.name!r}")
                definitions[result.name] = result.type

    predecessors: dict[str, set[str]] = {name: set() for name in reachable}
    for source in reachable:
        for target in successors[source]:
            if target in reachable:
                predecessors[target].add(source)

    # Phi results are available on entry to their block, but only after
    # each incoming edge has been validated against its predecessor's OUT.
    phi_names = {block.label: {phi.result.name for phi in block.phis}
                 for block in function.blocks}

    # Greatest fixed point for must-defined sets; the entry is anchored to
    # parameters, even when a loop has a back edge to the entry block.
    universe = set(definitions)
    incoming = {name: (set(parameters) if name == entry else set(universe)) for name in reachable}
    outgoing = {name: set(universe) for name in reachable}
    changed = True
    while changed:
        changed = False
        for block in function.blocks:
            label = block.label
            if label not in reachable:
                continue
            if label != entry:
                preds = predecessors[label]
                new_in = set.intersection(*(outgoing[pred] for pred in preds)) if preds else set()
            else:
                new_in = set(parameters)
            new_out = (new_in | phi_names[label] |
                       {instr.result.name for instr in block.instructions if instr.result is not None})
            if new_in != incoming[label] or new_out != outgoing[label]:
                incoming[label], outgoing[label] = new_in, new_out
                changed = True

    def require(value: QValue, available: set[str], block: str) -> None:
        if value.name not in available:
            raise QIRDataflowError(f"Block {block}: undefined value {value.name!r}")
        if definitions[value.name] != value.type:
            raise QIRDataflowError(f"Block {block}: inconsistent type for {value.name!r}")

    for block in function.blocks:
        if block.label not in reachable:
            continue
        for phi in block.phis:
            for source, value in phi.incoming:
                require(value, outgoing[source], source)
        available = set(incoming[block.label]) | phi_names[block.label]
        for instruction in block.instructions:
            for operand in instruction.operands:
                require(operand, available, block.label)
            if instruction.result is not None:
                available.add(instruction.result.name)
        term = block.terminator
        if isinstance(term, QBranch):
            require(term.condition, available, block.label)
        elif isinstance(term, QReturn) and term.value is not None:
            require(term.value, available, block.label)
