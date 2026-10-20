"""Conservative local integer constant folding for QIR."""
from dataclasses import replace
from .model import QFunction, QInstruction
from .operations import _fits_integer
from .types import is_integer
from .validation import validate_function


def fold_integer_constants(function: QFunction) -> QFunction:
    """Fold provably safe integer expressions within a basic block.

    Does not fold division, casts, floating point, or values across branches.
    An overflow is left for the runtime to diagnose, not silently wrapped.
    """
    validate_function(function)
    blocks = []
    for block in function.blocks:
        constants: dict[str, int] = {}
        instructions = []
        for instruction in block.instructions:
            op = instruction.opcode
            result = instruction.result
            candidate = None
            if op == "const" and result is not None:
                candidate = instruction.immediate
            elif op == "copy" and result is not None:
                candidate = constants.get(instruction.operands[0].name)
            elif (op in ("add", "sub", "mul") and result is not None
                  and is_integer(result.type) and len(instruction.operands) == 2):
                left, right = instruction.operands
                if left.name in constants and right.name in constants:
                    a, b = constants[left.name], constants[right.name]
                    computed = a + b if op == "add" else a - b if op == "sub" else a * b
                    if _fits_integer(computed, result.type.name):
                        candidate = computed
            if result is not None:
                constants.pop(result.name, None)
                if candidate is not None:
                    constants[result.name] = candidate
                    if op != "const":
                        instruction = QInstruction("const", (), result, candidate)
            # Stores and calls are never evaluated or removed.
            instructions.append(instruction)
        blocks.append(replace(block, instructions=tuple(instructions)))
    optimized = replace(function, blocks=tuple(blocks))
    validate_function(optimized)
    return optimized
