"""Versioned in-memory QRVM bytecode envelope (chapter 18.1).

This module does not serialize bytecode or change the existing QRVM runner.
"""
from dataclasses import dataclass
from typing import Any

from .instructions import OpCode


BYTECODE_MAGIC = "QVM"
BYTECODE_VERSION = (1, 0)


class BytecodeFormatError(ValueError):
    """An in-memory bytecode package has an invalid structure."""


@dataclass(frozen=True)
class BytecodeHeader:
    magic: str = BYTECODE_MAGIC
    major: int = BYTECODE_VERSION[0]
    minor: int = BYTECODE_VERSION[1]


def _validate_instructions(value: Any, location: str) -> None:
    if not isinstance(value, (list, tuple)):
        raise BytecodeFormatError(f"{location}: instructions must be a sequence")
    for index, instruction in enumerate(value):
        if not isinstance(instruction, (list, tuple)) or len(instruction) != 2:
            raise BytecodeFormatError(f"{location}[{index}]: expected opcode and operand")
        if not isinstance(instruction[0], OpCode):
            raise BytecodeFormatError(f"{location}[{index}]: unknown opcode")
        # Operand schemas and control-flow checks belong to the later verifier.


def validate_bytecode_package(package: Any) -> None:
    """Validate the envelope and existing compiler package shape.

    Returns None on success and raises BytecodeFormatError otherwise.
    This is structural validation, NOT a security verifier.
    """
    if not isinstance(package, dict):
        raise BytecodeFormatError("bytecode package must be a dictionary")
    header = package.get("header")
    if not isinstance(header, BytecodeHeader):
        raise BytecodeFormatError("missing bytecode header")
    if header.magic != BYTECODE_MAGIC or header.major != BYTECODE_VERSION[0]:
        raise BytecodeFormatError("unsupported bytecode format")
    if not isinstance(header.minor, int) or header.minor < 0 or header.minor > BYTECODE_VERSION[1]:
        raise BytecodeFormatError("unsupported bytecode minor version")
    _validate_instructions(package.get("instructions"), "main")
    for table_name in ("functions", "class_methods"):
        table = package.get(table_name, {})
        if not isinstance(table, dict):
            raise BytecodeFormatError(f"{table_name} must be a dictionary")
        for name, function in table.items():
            if not isinstance(function, dict):
                raise BytecodeFormatError(f"{table_name}[{name!r}] must be a dictionary")
            if not isinstance(function.get("parameters"), (list, tuple)):
                raise BytecodeFormatError(f"{table_name}[{name!r}]: missing parameters")
            if not isinstance(function.get("return_type"), str):
                raise BytecodeFormatError(f"{table_name}[{name!r}]: missing return type")
            _validate_instructions(function.get("instructions"), f"{table_name}[{name!r}]")


def wrap_legacy_program(program: Any) -> dict[str, Any]:
    """Add a versioned envelope without mutating the existing compiler output.

    Returns a shallow copy; instruction lists and function bodies are shared.
    """
    if isinstance(program, (list, tuple)):
        result: dict[str, Any] = {"instructions": program, "functions": {}, "class_methods": {}}
    elif isinstance(program, dict):
        result = dict(program)
    else:
        raise BytecodeFormatError("unsupported legacy program")
    if "header" in result:
        raise BytecodeFormatError("program already contains a header")
    result["header"] = BytecodeHeader()
    validate_bytecode_package(result)
    return result
