"""Validated in-memory bytecode loading for the Python QRVM bootstrap.

Loading does not execute code. Opcode operand and control-flow verification
are deliberately deferred to the later bytecode verifier.
"""
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from .bytecode_format import (
    BytecodeFormatError,
    BytecodeHeader,
    validate_bytecode_package,
    wrap_legacy_program,
)
from .bytecode_verifier import BytecodeVerificationError, verify_bytecode


class BytecodeLoadError(ValueError):
    """A bytecode program cannot be prepared for execution."""


@dataclass(frozen=True)
class LoadedBytecode:
    """Validated snapshot of a versioned, in-memory bytecode package."""

    header: BytecodeHeader
    package: dict[str, Any]


def load_bytecode(program: Any, *, allow_legacy: bool = False, verify: bool = False) -> LoadedBytecode:
    """Validate and snapshot a bytecode program without executing it.

    Legacy inputs require explicit opt-in. The returned package is an isolated
    deep copy, so later changes to the source program do not affect execution.
    Returns a LoadedBytecode ready to be passed to run_loaded_bytecode().
    """
    try:
        if isinstance(program, LoadedBytecode):
            package = program.package
        elif isinstance(program, dict) and "header" in program:
            package = program
        elif allow_legacy:
            package = wrap_legacy_program(program)
        else:
            raise BytecodeLoadError("unversioned bytecode requires allow_legacy=True")
        validate_bytecode_package(package)
        snapshot = deepcopy(package)
        validate_bytecode_package(snapshot)
        if verify:
            verify_bytecode(snapshot)
        return LoadedBytecode(header=snapshot["header"], package=snapshot)
    except (BytecodeFormatError, BytecodeVerificationError, TypeError, RecursionError) as exc:
        raise BytecodeLoadError(f"invalid bytecode package: {exc}") from exc


def run_loaded_bytecode(vm: Any, loaded: LoadedBytecode) -> None:
    """Execute a validated snapshot using the existing QRVM instance.

    Revalidate because LoadedBytecode.package is a mutable dictionary. The VM
    receives its own copy so runtime changes cannot mutate the loaded program.
    Returns None; the VM retains the resulting execution state.
    """
    if not isinstance(loaded, LoadedBytecode):
        raise BytecodeLoadError("expected LoadedBytecode")
    try:
        validate_bytecode_package(loaded.package)
    except BytecodeFormatError as exc:
        raise BytecodeLoadError(f"invalid loaded bytecode: {exc}") from exc
    if loaded.header != loaded.package["header"]:
        raise BytecodeLoadError("loaded header does not match package header")
    vm.run(deepcopy(loaded.package))
