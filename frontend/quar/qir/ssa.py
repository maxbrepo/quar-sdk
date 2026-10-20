"""Conservative automatic SSA conversion for acyclic QIR control-flow graphs.

The input uses QInstruction results as mutable local assignments. Conversion
renames definitions and inserts QPhi at join blocks. Loops are explicitly
rejected until loop-carried SSA construction is implemented.
"""
from __future__ import annotations

from dataclasses import replace
from .model import QBlock, QBranch, QFunction, QInstruction, QJump, QPhi, QReturn, QValue
from .validation import validate_function


class QIRSSAError(ValueError):
    """Raised for unsupported or ambiguous SSA conversion inputs."""


def to_ssa(function: QFunction) -> QFunction:
    """Convert reachable acyclic QIR assignments to single-assignment form.

    Returns a new validated function; never mutates the input. All source
    variables must be defined on every path before use. Explicit phi nodes,
    unreachable blocks and cyclic control flow are currently unsupported.
    """
    blocks = {block.label: block for block in function.blocks}
    if not blocks or len(blocks) != len(function.blocks):
        raise QIRSSAError('Function requires uniquely named blocks')
    if any(block.phis for block in function.blocks):
        raise QIRSSAError('Existing phi nodes are not supported by automatic conversion')
    entry = function.blocks[0].label
    successors = {}
    predecessors = {label: set() for label in blocks}
    for block in function.blocks:
        term = block.terminator
        targets = ((term.target,) if isinstance(term, QJump) else
                   (term.true_target, term.false_target) if isinstance(term, QBranch) else
                   () if isinstance(term, QReturn) else None)
        if targets is None or any(target not in blocks for target in targets):
            raise QIRSSAError('Invalid control-flow terminator or target')
        successors[block.label] = tuple(dict.fromkeys(targets))
        for target in targets:
            predecessors[target].add(block.label)
    if predecessors[entry]:
        raise QIRSSAError('Entry block must not have incoming edges')
    # Kahn's algorithm also rejects cycles; process joins only after all inputs.
    pending = {label: len(preds) for label, preds in predecessors.items()}
    ready = [entry]
    order = []
    while ready:
        label = ready.pop(0)
        order.append(label)
        for target in successors[label]:
            pending[target] -= 1
            if pending[target] == 0:
                ready.append(target)
    if len(order) != len(blocks):
        raise QIRSSAError('Loops or unreachable blocks require a later SSA pass')

    parameter_names = {p.name for p in function.parameters}
    if len(parameter_names) != len(function.parameters):
        raise QIRSSAError('Duplicate parameter name')
    used_names = set(parameter_names)
    for block in function.blocks:
        for instruction in block.instructions:
            if instruction.result is not None:
                used_names.add(instruction.result.name)
    serial = 0

    def fresh(base: str) -> str:
        nonlocal serial
        while True:
            serial += 1
            name = f'{base}$ssa{serial}'
            if name not in used_names:
                used_names.add(name)
                return name

    outgoing: dict[str, dict[str, QValue]] = {}
    rewritten: dict[str, QBlock] = {}
    for label in order:
        block = blocks[label]
        preds = sorted(predecessors[label])
        phis = []
        if not preds:
            environment = {p.name: p for p in function.parameters}
        else:
            environments = [outgoing[pred] for pred in preds]
            # A value is available after a join only if all paths define it.
            common = set.intersection(*(set(env) for env in environments))
            environment = {}
            for name in sorted(common):
                values = [env[name] for env in environments]
                if any(v.type != values[0].type for v in values):
                    raise QIRSSAError(f'Conflicting types for {name!r} at {label}')
                if all(v == values[0] for v in values):
                    environment[name] = values[0]
                else:
                    result = QValue(fresh(name), values[0].type)
                    phis.append(QPhi(result, tuple(zip(preds, values))))
                    environment[name] = result
        instructions = []
        for instruction in block.instructions:
            operands = []
            for operand in instruction.operands:
                value = environment.get(operand.name)
                if value is None or value.type != operand.type:
                    raise QIRSSAError(f'Undefined or mismatched value {operand.name!r} in {label}')
                operands.append(value)
            result = instruction.result
            new_result = None
            if result is not None:
                if not result.name:
                    raise QIRSSAError('Empty assignment name')
                new_result = QValue(fresh(result.name), result.type)
                environment[result.name] = new_result
            instructions.append(replace(instruction, operands=tuple(operands), result=new_result))
        term = block.terminator
        if isinstance(term, QBranch):
            condition = environment.get(term.condition.name)
            if condition is None or condition.type != term.condition.type:
                raise QIRSSAError(f'Undefined branch condition in {label}')
            term = replace(term, condition=condition)
        elif isinstance(term, QReturn) and term.value is not None:
            value = environment.get(term.value.name)
            if value is None or value.type != term.value.type:
                raise QIRSSAError(f'Undefined return value in {label}')
            term = replace(term, value=value)
        outgoing[label] = dict(environment)
        rewritten[label] = QBlock(label, tuple(instructions), term, tuple(phis))
    result = replace(function, blocks=tuple(rewritten[b.label] for b in function.blocks))
    validate_function(result)
    return result
