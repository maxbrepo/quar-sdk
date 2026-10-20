"""Conservative SSA integer constant propagation across QIR basic blocks."""
from __future__ import annotations

from dataclasses import replace

from .model import QBranch, QFunction, QJump, QInstruction, QReturn
from .operations import _fits_integer
from .types import is_integer
from .validation import validate_function


def propagate_integer_constants(function: QFunction) -> QFunction:
    """Return a new QIR function with safe cross-block integer folding.

    This is a monotone, SSA-name-based analysis. Phi values are constant only
    when every incoming edge supplies the same known integer. Unknown values
    remain unknown, including loop-carried cycles without an established seed.
    It never rewrites branch conditions or removes side-effecting instructions.
    """
    validate_function(function)
    blocks = {block.label: block for block in function.blocks}
    entry = function.blocks[0].label
    reachable = {entry}
    pending = [entry]
    while pending:
        block = blocks[pending.pop()]
        term = block.terminator
        targets = ((term.target,) if isinstance(term, QJump) else
                   (term.true_target, term.false_target) if isinstance(term, QBranch) else ())
        for target in targets:
            if target not in reachable:
                reachable.add(target)
                pending.append(target)

    constants: dict[str, int] = {}

    def evaluate(instruction: QInstruction) -> int | None:
        result = instruction.result
        if result is None or not is_integer(result.type):
            return None
        op = instruction.opcode
        if op == "const":
            return instruction.immediate
        if op == "copy" and len(instruction.operands) == 1:
            return constants.get(instruction.operands[0].name)
        if op not in ("add", "sub", "mul") or len(instruction.operands) != 2:
            return None
        a = constants.get(instruction.operands[0].name)
        b = constants.get(instruction.operands[1].name)
        if a is None or b is None:
            return None
        value = a + b if op == "add" else a - b if op == "sub" else a * b
        return value if _fits_integer(value, result.type.name) else None

    # SSA definitions have unique names, so discoveries cannot be invalidated.
    # A bounded pass count ensures termination even with malformed extensions.
    definitions = sum((len(block.phis) + len(block.instructions)
                       for block in function.blocks if block.label in reachable), 0)
    for _ in range(definitions + 1):
        changed = False
        for block in function.blocks:
            if block.label not in reachable:
                continue
            for phi in block.phis:
                if phi.result.name in constants or not is_integer(phi.result.type):
                    continue
                incoming = [constants.get(value.name) for _, value in phi.incoming]
                if incoming and all(value is not None and value == incoming[0] for value in incoming):
                    constants[phi.result.name] = incoming[0]
                    changed = True
            for instruction in block.instructions:
                if instruction.result is None or instruction.result.name in constants:
                    continue
                value = evaluate(instruction)
                if value is not None:
                    constants[instruction.result.name] = value
                    changed = True
        if not changed:
            break

    rewritten = []
    for block in function.blocks:
        instructions = []
        for instruction in block.instructions:
            result = instruction.result
            if (block.label in reachable and result is not None and
                    result.name in constants and instruction.opcode in ("copy", "add", "sub", "mul")):
                instruction = QInstruction("const", (), result, constants[result.name], instruction.metadata)
            instructions.append(instruction)
        rewritten.append(replace(block, instructions=tuple(instructions)))
    optimized = replace(function, blocks=tuple(rewritten))
    validate_function(optimized)
    return optimized
