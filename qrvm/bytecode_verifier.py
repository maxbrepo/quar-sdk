"""Opt-in structural and conservative stack verifier for QRVM bytecode.

This bootstrap pass is not a proof of type, memory or control-flow safety.
"""
from collections import deque
from dataclasses import dataclass
from typing import Any

from .bytecode_format import validate_bytecode_package
from .instructions import OpCode


class BytecodeVerificationError(ValueError):
    """A bytecode instruction fails a pre-execution verification rule."""


@dataclass(frozen=True)
class VerificationReport:
    bodies: int
    instructions: int
    stack_checked_bodies: int


# Only instructions with an unambiguous, local stack effect are modeled.
_EFFECTS = {
    OpCode.PUSH_INT: (0, 1), OpCode.PUSH_DOUBLE: (0, 1),
    OpCode.PUSH_BOOL: (0, 1), OpCode.PUSH_CHAR: (0, 1),
    OpCode.PUSH_STRING: (0, 1), OpCode.LOAD: (0, 1),
    OpCode.STORE: (1, 0), OpCode.POP: (1, 0),
    OpCode.ADD: (2, 1), OpCode.SUB: (2, 1),
    OpCode.MUL: (2, 1), OpCode.DIV: (2, 1),
    OpCode.MOD: (2, 1), OpCode.BIT_AND: (2, 1),
    OpCode.BIT_OR: (2, 1), OpCode.BIT_XOR: (2, 1),
    OpCode.SHIFT_LEFT: (2, 1), OpCode.SHIFT_RIGHT: (2, 1),
    OpCode.EQUAL: (2, 1), OpCode.NOT_EQUAL: (2, 1),
    OpCode.LESS: (2, 1), OpCode.LESS_EQUAL: (2, 1),
    OpCode.GREATER: (2, 1), OpCode.GREATER_EQUAL: (2, 1),
    OpCode.LOGICAL_AND: (2, 1), OpCode.LOGICAL_OR: (2, 1),
    OpCode.NEGATE: (1, 1), OpCode.LOGICAL_NOT: (1, 1),
    OpCode.BIT_NOT: (1, 1), OpCode.PRINT: (1, 0),
    OpCode.JUMP_IF_FALSE: (1, 0), OpCode.JUMP: (0, 0),
    OpCode.HALT: (0, 0),
}


def _verify_body(instructions: Any, location: str) -> bool:
    size = len(instructions)
    for index, (opcode, operand) in enumerate(instructions):
        where = f"{location}[{index}] {opcode.name}"
        if opcode in (OpCode.JUMP, OpCode.JUMP_IF_FALSE):
            if type(operand) is not int or not 0 <= operand <= size:
                raise BytecodeVerificationError(f"{where}: invalid jump target")
        elif opcode == OpCode.CALL:
            if (not isinstance(operand, tuple) or len(operand) != 2 or
                    not isinstance(operand[0], str) or not operand[0] or
                    type(operand[1]) is not int or operand[1] < 0):
                raise BytecodeVerificationError(f"{where}: invalid call metadata")
        elif opcode in (OpCode.LOAD, OpCode.STORE):
            if not isinstance(operand, str) or not operand:
                raise BytecodeVerificationError(f"{where}: invalid variable name")
        elif opcode == OpCode.PUSH_INT:
            if type(operand) is not int:
                raise BytecodeVerificationError(f"{where}: expected int operand")
        elif opcode == OpCode.PUSH_DOUBLE:
            if type(operand) is not float:
                raise BytecodeVerificationError(f"{where}: expected float operand")
        elif opcode == OpCode.PUSH_BOOL:
            if type(operand) is not bool:
                raise BytecodeVerificationError(f"{where}: expected bool operand")
        elif opcode == OpCode.PUSH_STRING:
            if not isinstance(operand, str):
                raise BytecodeVerificationError(f"{where}: expected string operand")
        elif opcode == OpCode.PUSH_CHAR:
            if not isinstance(operand, str) or len(operand) > 1:
                raise BytecodeVerificationError(f"{where}: invalid character operand")

    # An unknown stack effect makes depth analysis inconclusive. Do not infer
    # safety from it, and never reject valid programs on an invented effect.
    if any(opcode not in _EFFECTS for opcode, _ in instructions):
        return False
    # Propagate the minimum possible depth at each instruction. Each negative
    # path is rejected; joins with unequal depths are allowed conservatively.
    depths = {0: 0}
    pending = deque([0])
    while pending:
        index = pending.popleft()
        if index == size:
            continue
        opcode, operand = instructions[index]
        consumed, produced = _EFFECTS[opcode]
        depth = depths[index]
        if depth < consumed:
            raise BytecodeVerificationError(
                f"{location}[{index}] {opcode.name}: stack underflow")
        after = depth - consumed + produced
        if opcode == OpCode.HALT:
            successors = ()
        elif opcode == OpCode.JUMP:
            successors = (operand,)
        elif opcode == OpCode.JUMP_IF_FALSE:
            successors = (operand, index + 1)
        else:
            successors = (index + 1,)
        for target in successors:
            if target not in depths or after < depths[target]:
                depths[target] = after
                pending.append(target)
    return True


def verify_bytecode(package: Any) -> VerificationReport:
    """Check a versioned package without modifying or executing it."""
    validate_bytecode_package(package)
    bodies = [("main", package["instructions"])]
    for table_name in ("functions", "class_methods"):
        bodies.extend((f"{table_name}[{name!r}]", value["instructions"])
                      for name, value in package.get(table_name, {}).items())
    checked = sum(_verify_body(instructions, name) for name, instructions in bodies)
    return VerificationReport(len(bodies), sum(len(code) for _, code in bodies), checked)
