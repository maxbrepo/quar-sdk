"""Loop-aware SSA conversion using stable names and fixed-point propagation.

The converter supports reachable, reducible loops with an explicit preheader.
Irreducible graphs and uses lacking a definition on every path are rejected.
"""
from __future__ import annotations

from dataclasses import replace
from .model import QBlock, QBranch, QFunction, QJump, QPhi, QReturn, QValue
from .ssa import QIRSSAError, to_ssa
from .validation import validate_function


def to_ssa_with_loops(function: QFunction) -> QFunction:
    """Convert assignments in a reachable CFG, including loop-carried values.

    Return a new function; the input is never mutated. Loop headers require
    a non-backedge entry path. This is not a general irreducible-CFG pass.
    """
    blocks = {b.label: b for b in function.blocks}
    if not blocks or len(blocks) != len(function.blocks):
        raise QIRSSAError("Blocks must have unique labels")
    if any(b.phis for b in function.blocks):
        raise QIRSSAError("Preexisting phi nodes are not supported")
    entry = function.blocks[0].label
    succ = {}
    preds = {name: set() for name in blocks}
    for block in function.blocks:
        term = block.terminator
        targets = ((term.target,) if isinstance(term, QJump) else
                   (term.true_target, term.false_target) if isinstance(term, QBranch) else
                   () if isinstance(term, QReturn) else None)
        if targets is None or any(t not in blocks for t in targets):
            raise QIRSSAError("Invalid control-flow target")
        succ[block.label] = tuple(dict.fromkeys(targets))
        for target in targets:
            preds[target].add(block.label)
    if preds[entry]:
        raise QIRSSAError("Entry block cannot have incoming edges")
    reachable = {entry}
    queue = [entry]
    while queue:
        for target in succ[queue.pop(0)]:
            if target not in reachable:
                reachable.add(target)
                queue.append(target)
    if len(reachable) != len(blocks):
        raise QIRSSAError("Unreachable blocks are not supported")
    # Fast path retains the exact established behavior for acyclic graphs.
    remaining = {name: len(preds[name]) for name in blocks}
    ready = [entry]
    visited = 0
    while ready:
        name = ready.pop(0)
        visited += 1
        for target in succ[name]:
            remaining[target] -= 1
            if remaining[target] == 0:
                ready.append(target)
    if visited == len(blocks):
        return to_ssa(function)

    parameters = {v.name: v for v in function.parameters}
    if len(parameters) != len(function.parameters):
        raise QIRSSAError("Duplicate parameter")
    reserved = set(parameters)
    for block in function.blocks:
        for instr in block.instructions:
            if instr.result is not None:
                reserved.add(instr.result.name)
    counter = 0
    def fresh(base: str) -> str:
        nonlocal counter
        while True:
            counter += 1
            candidate = f"{base}$ssa{counter}"
            if candidate not in reserved:
                reserved.add(candidate)
                return candidate

    definitions = {}
    for block in function.blocks:
        for index, instr in enumerate(block.instructions):
            if instr.result is not None:
                definitions[block.label, index] = QValue(fresh(instr.result.name), instr.result.type)

    # Establish a stable phi candidate for each variable at every join. A
    # candidate becomes an actual phi only when incoming versions differ.
    names = set(parameters)
    for block in function.blocks:
        for instr in block.instructions:
            if instr.result is not None:
                names.add(instr.result.name)
    phi_candidates = {}
    for block in function.blocks:
        if len(preds[block.label]) > 1:
            for name in sorted(names):
                phi_candidates[block.label, name] = None
    incoming = {name: dict(parameters) for name in blocks}
    outgoing = {name: dict(parameters) for name in blocks}
    for block in function.blocks:
        for index, instr in enumerate(block.instructions):
            if instr.result is not None:
                outgoing[block.label][instr.result.name] = definitions[block.label, index]
    phi_active = {name: set() for name in blocks}
    # Iteration over finite symbolic versions; phi identities never change.
    limit = max(20, len(blocks) * (len(names) + 1) * 8)
    for _ in range(limit):
        changed = False
        for block in function.blocks:
            label = block.label
            if label == entry:
                env = dict(parameters)
                active = set()
            else:
                env = {}
                active = set()
                for name in sorted(names):
                    values = [outgoing[p].get(name) for p in sorted(preds[label])]
                    if not values or any(v is None for v in values):
                        continue
                    if any(v.type != values[0].type for v in values):
                        raise QIRSSAError(f"Conflicting types for {name!r} at {label}")
                    if all(v == values[0] for v in values):
                        env[name] = values[0]
                    else:
                        key = (label, name)
                        if key not in phi_candidates:
                            raise QIRSSAError("Ambiguous loop entry")
                        if phi_candidates[key] is None:
                            phi_candidates[key] = QValue(fresh(name), values[0].type)
                        env[name] = phi_candidates[key]
                        active.add(name)
            result_env = dict(env)
            for index, instr in enumerate(block.instructions):
                if instr.result is not None:
                    result_env[instr.result.name] = definitions[label, index]
            if env != incoming[label] or result_env != outgoing[label] or active != phi_active[label]:
                incoming[label], outgoing[label], phi_active[label] = env, result_env, active
                changed = True
        if not changed:
            break
    else:
        raise QIRSSAError("Loop SSA analysis did not converge")

    rewritten = []
    for block in function.blocks:
        label = block.label
        env = dict(incoming[label])
        phis = []
        for name in sorted(phi_active[label]):
            values = tuple((pred, outgoing[pred][name]) for pred in sorted(preds[label]))
            phis.append(QPhi(phi_candidates[label, name], values))
        instructions = []
        for index, instr in enumerate(block.instructions):
            operands = []
            for operand in instr.operands:
                actual = env.get(operand.name)
                if actual is None or actual.type != operand.type:
                    raise QIRSSAError(f"Undefined or mismatched value {operand.name!r} in {label}")
                operands.append(actual)
            result = definitions.get((label, index))
            instructions.append(replace(instr, operands=tuple(operands), result=result))
            if result is not None:
                env[instr.result.name] = result
        term = block.terminator
        if isinstance(term, QBranch):
            value = env.get(term.condition.name)
            if value is None or value.type != term.condition.type:
                raise QIRSSAError(f"Undefined branch condition in {label}")
            term = replace(term, condition=value)
        elif isinstance(term, QReturn) and term.value is not None:
            value = env.get(term.value.name)
            if value is None or value.type != term.value.type:
                raise QIRSSAError(f"Undefined return value in {label}")
            term = replace(term, value=value)
        rewritten.append(QBlock(label, tuple(instructions), term, tuple(phis)))
    result = replace(function, blocks=tuple(rewritten))
    try:
        validate_function(result)
    except ValueError as exc:
        raise QIRSSAError(f"Invalid converted SSA: {exc}") from exc
    return result
