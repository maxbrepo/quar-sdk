"""Opt-in QIR-to-QRVM function adapter for a conservative linear i32 subset.

This adapter does not change the default AST compiler. It accepts validated,
SSA-form QIR and rejects unsupported types, operations and control flow.
It is an experimental function-level route, not a whole-program migration.
"""
from __future__ import annotations

from frontend.quar.qir.model import QFunction, QReturn
from frontend.quar.qir.validation import validate_function
from .instructions import OpCode


class QIRQRVMBackendError(ValueError):
    """QIR is valid but not yet supported by the experimental QRVM adapter."""


_BINARY = {"add": OpCode.ADD, "sub": OpCode.SUB, "mul": OpCode.MUL}


def compile_qir_function(function: QFunction) -> dict:
    """Compile one linear i32 QIR function to the existing QRVM function ABI.

    Returns a QRVM function dictionary. All unsupported semantics fail closed.
    Arithmetic is restricted to the initial unchecked i32 subset: callers
    must not treat this as a memory-safety or overflow-parity certification.
    """
    validate_function(function)
    if function.return_type.name != "i32" or any(p.type.name != "i32" for p in function.parameters):
        raise QIRQRVMBackendError("Initial adapter requires i32 parameters and return")
    if len(function.blocks) != 1 or function.blocks[0].phis:
        raise QIRQRVMBackendError("Initial adapter requires one block without phi nodes")
    block = function.blocks[0]
    if not isinstance(block.terminator, QReturn) or block.terminator.value is None:
        raise QIRQRVMBackendError("Initial adapter requires a value return")
    instructions = []
    for operation in block.instructions:
        if operation.metadata and operation.metadata.safety.checks:
            raise QIRQRVMBackendError("Runtime safety obligations are not implemented")
        if operation.result is None or operation.result.type.name != "i32":
            raise QIRQRVMBackendError("Initial adapter requires i32 SSA results")
        if operation.opcode == "const":
            instructions.append((OpCode.PUSH_INT, operation.immediate))
        elif operation.opcode == "copy":
            instructions.append((OpCode.LOAD, operation.operands[0].name))
        elif operation.opcode in _BINARY:
            if any(value.type.name != "i32" for value in operation.operands):
                raise QIRQRVMBackendError("Initial adapter requires i32 operands")
            instructions.extend((OpCode.LOAD, value.name) for value in operation.operands)
            instructions.append((_BINARY[operation.opcode], None))
        else:
            raise QIRQRVMBackendError(f"Unsupported QIR operation: {operation.opcode}")
        instructions.append((OpCode.STORE, operation.result.name))
    instructions.append((OpCode.LOAD, block.terminator.value.name))
    instructions.append((OpCode.RETURN, True))
    return {"parameters": [p.name for p in function.parameters],
            "return_type": "int", "instructions": instructions}
