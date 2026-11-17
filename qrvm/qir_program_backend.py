"""Opt-in QIR-to-QRVM backend for scoped i32 programs and branches."""
from __future__ import annotations

from frontend.quar.qir.model import QBranch, QFunction, QJump, QModule, QReturn
from frontend.quar.qir.validation import validate_module
from .instructions import OpCode


class QIRProgramBackendError(ValueError):
    """Validated QIR exceeds the supported experimental QRVM backend subset."""


_BINARY = {"add": OpCode.ADD, "sub": OpCode.SUB, "mul": OpCode.MUL, "div": OpCode.DIV, "mod": OpCode.MOD}


def _compile_function(function: QFunction, *, entry: bool) -> list[tuple[OpCode, object]]:
    """Compile QIR CFG to QRVM bytecode, resolving phi values on each edge.

    Returns instructions with absolute, function-local branch addresses.
    No AST or legacy IR is consulted.
    """
    if entry:
        if function.return_type.name != "void" or function.parameters:
            raise QIRProgramBackendError("Invalid QIR entry function")
    elif (function.return_type.name not in ("i32", "bool", "void") or
          any(p.type.name != "i32" for p in function.parameters)):
        raise QIRProgramBackendError("Only i32 functions with value returns are supported")

    blocks = {block.label: block for block in function.blocks}
    # Edge-specific phi transfers are emitted as parallel copies, including
    # loop backedges. Acyclic-only restrictions are no longer needed.
    for block in function.blocks:
        if isinstance(block.terminator, QJump) and block.terminator.target == block.label:
            raise QIRProgramBackendError("Unconditional self-loop is not supported")
    instructions: list[tuple[OpCode, object]] = []
    labels: dict[str, int] = {}
    fixups: list[tuple[int, str]] = []
    comparisons = {"eq": OpCode.EQUAL, "ne": OpCode.NOT_EQUAL,
                   "lt": OpCode.LESS, "le": OpCode.LESS_EQUAL,
                   "gt": OpCode.GREATER, "ge": OpCode.GREATER_EQUAL}

    def emit_jump(opcode: OpCode, label: str) -> None:
        """Append a forward or backward jump for later address resolution."""
        fixups.append((len(instructions), label))
        instructions.append((opcode, None))

    def emit_phi_moves(target: str, source: str) -> None:
        """Snapshot all incoming values before writing any phi destination."""
        incoming_pairs = [(phi.result.name, dict(phi.incoming)[source].name)
                          for phi in blocks[target].phis]
        for index, (_, value_name) in enumerate(incoming_pairs):
            temp = f"$qir_edge_{function.name}_{source}_{target}_{index}"
            instructions.extend(((OpCode.LOAD, value_name), (OpCode.STORE, temp)))
        for index, (destination, _) in enumerate(incoming_pairs):
            temp = f"$qir_edge_{function.name}_{source}_{target}_{index}"
            instructions.extend(((OpCode.LOAD, temp), (OpCode.STORE, destination)))

    for block in function.blocks:
        labels[block.label] = len(instructions)
        for operation in block.instructions:
            if operation.metadata and operation.metadata.safety.checks and operation.opcode not in ("array_get", "array_set"):
                raise QIRProgramBackendError("Unimplemented runtime safety obligation")
            if operation.opcode == "array_set":
                array, index, value = operation.operands
                if array.type.name != "ptr<i32>" or index.type.name != "i32" or value.type.name != "i32":
                    raise QIRProgramBackendError("Invalid array store")
                instructions.extend(((OpCode.LOAD, index.name), (OpCode.LOAD, value.name),
                                     (OpCode.ARRAY_STORE, (array.name, False))))
                continue
            if operation.opcode == "print":
                if len(operation.operands) != 1 or operation.operands[0].type.name not in ("i32", "bool"):
                    raise QIRProgramBackendError("Only i32 and bool print are supported")
                instructions.extend(((OpCode.LOAD, operation.operands[0].name), (OpCode.PRINT, None)))
                continue
            if operation.opcode in ("call_void", "native_call_void"):
                if operation.result is not None or any(value.type.name not in (("i32", "u32", "u64", "bool", "string", "opaque") if operation.opcode == "native_call_void" else ("i32",)) for value in operation.operands):
                    raise QIRProgramBackendError("Invalid void call")
                instructions.extend((OpCode.LOAD, value.name) for value in operation.operands)
                instructions.append((OpCode.CALL, (operation.immediate, len(operation.operands))))
                if operation.opcode == "native_call_void":
                    instructions.append((OpCode.POP, None))
                continue
            if operation.result is None:
                raise QIRProgramBackendError("QIR result is required")
            if operation.opcode == "array_alloc" and operation.result.type.name == "ptr<i32>":
                instructions.append((OpCode.ARRAY_NEW, (operation.result.name, operation.immediate, 0, 0, None)))
                continue
            elif operation.opcode == "array_get" and operation.result.type.name == "i32":
                array, index = operation.operands
                if array.type.name != "ptr<i32>" or index.type.name != "i32":
                    raise QIRProgramBackendError("Invalid array load")
                instructions.extend(((OpCode.LOAD, index.name), (OpCode.ARRAY_LOAD, (array.name, False))))
            elif operation.opcode == "string_const" and operation.result.type.name == "string":
                if type(operation.immediate) is not str or "\x00" in operation.immediate:
                    raise QIRProgramBackendError("Invalid native string constant")
                instructions.append((OpCode.PUSH_STRING, operation.immediate))
            elif operation.opcode == "const" and operation.result.type.name in ("i32", "u32", "u64"):
                if (type(operation.immediate) is not int or
                        (operation.result.type.name in ("u32", "u64") and not 0 <= operation.immediate <= ((1 << (32 if operation.result.type.name == "u32" else 64)) - 1))):
                    raise QIRProgramBackendError("Invalid integer constant")
                instructions.append((OpCode.PUSH_INT, operation.immediate))
            elif operation.opcode == "const" and operation.result.type.name == "bool" and type(operation.immediate) is bool:
                instructions.append((OpCode.PUSH_BOOL, operation.immediate))
            elif operation.opcode == "logical_not" and operation.result.type.name == "bool":
                if len(operation.operands) != 1 or operation.operands[0].type.name != "bool":
                    raise QIRProgramBackendError("Logical NOT requires one bool operand")
                instructions.append((OpCode.LOAD, operation.operands[0].name))
                instructions.append((OpCode.LOGICAL_NOT, None))
            elif operation.opcode == "copy" and operation.result.type.name in ("i32", "u32", "u64"):
                instructions.append((OpCode.LOAD, operation.operands[0].name))
            elif operation.opcode in _BINARY and operation.result.type.name == "i32":
                if any(value.type.name != "i32" for value in operation.operands):
                    raise QIRProgramBackendError("Only i32 arithmetic is supported")
                instructions.extend((OpCode.LOAD, value.name) for value in operation.operands)
                instructions.append((_BINARY[operation.opcode], None))
            elif operation.opcode in comparisons and operation.result.type.name == "bool":
                if any(value.type.name != "i32" for value in operation.operands):
                    raise QIRProgramBackendError("Only i32 comparisons are supported")
                instructions.extend((OpCode.LOAD, value.name) for value in operation.operands)
                instructions.append((comparisons[operation.opcode], None))
            elif operation.opcode in ("call", "native_call") and operation.result.type.name in ("i32", "u32", "u64", "bool", "opaque", "string"):
                if any(value.type.name not in (("i32", "u32", "u64", "bool", "string", "opaque") if operation.opcode == "native_call" else ("i32",)) for value in operation.operands):
                    raise QIRProgramBackendError("Unsupported call argument type")
                instructions.extend((OpCode.LOAD, value.name) for value in operation.operands)
                instructions.append((OpCode.CALL, (operation.immediate, len(operation.operands))))
            else:
                raise QIRProgramBackendError(f"Unsupported operation: {operation.opcode}")
            instructions.append((OpCode.STORE, operation.result.name))

        term = block.terminator
        if isinstance(term, QJump):
            emit_phi_moves(term.target, block.label)
            emit_jump(OpCode.JUMP, term.target)
        elif isinstance(term, QBranch):
            instructions.append((OpCode.LOAD, term.condition.name))
            false_edge_jump = len(instructions)
            instructions.append((OpCode.JUMP_IF_FALSE, None))
            emit_phi_moves(term.true_target, block.label)
            emit_jump(OpCode.JUMP, term.true_target)
            false_edge_start = len(instructions)
            instructions[false_edge_jump] = (OpCode.JUMP_IF_FALSE, false_edge_start)
            emit_phi_moves(term.false_target, block.label)
            emit_jump(OpCode.JUMP, term.false_target)
        elif isinstance(term, QReturn):
            if entry:
                if term.value is not None:
                    raise QIRProgramBackendError("Entry function cannot return a value")
                instructions.append((OpCode.HALT, None))
            else:
                if term.value is None:
                    if function.return_type.name != "void":
                        raise QIRProgramBackendError("Value-returning function must return a value")
                    instructions.append((OpCode.RETURN, None))
                else:
                    instructions.extend(((OpCode.LOAD, term.value.name), (OpCode.RETURN, True)))
        else:
            raise QIRProgramBackendError("Unsupported terminator")

    for index, target in fixups:
        instructions[index] = (instructions[index][0], labels[target])
    return instructions


def compile_qir_program(module: QModule) -> dict:
    """Compile validated QIR to a QRVM package with independent call frames."""
    validate_module(module)
    if not module.functions or module.functions[0].name != "__qir_entry":
        raise QIRProgramBackendError("Expected QIR entry function first")
    entry = _compile_function(module.functions[0], entry=True)
    functions = {}
    for function in module.functions[1:]:
        functions[function.name] = {
            "parameters": [p.name for p in function.parameters],
            "return_type": "bool" if function.return_type.name == "bool" else "void" if function.return_type.name == "void" else "int",
            "instructions": _compile_function(function, entry=False),
        }
    return {"instructions": entry, "functions": functions, "class_methods": {},
            "native_declarations": {name: (args, result)
                                    for name, args, result in module.native_declarations}}
