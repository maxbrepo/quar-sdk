"""Small, executable C99 adapter for the validated QIR i32 subset.

This adapter does not replace the legacy C backend or discharge safety checks.
"""
from __future__ import annotations

import re

from .backend_readiness import inspect_backend_readiness
from .model import QFunction, QReturn


class QIRCBackendError(ValueError):
    """Raised when QIR cannot be safely lowered to the initial C subset."""


def emit_c_function(function: QFunction) -> str:
    """Emit a standalone C99 function for the supported, validated QIR subset.

    Returns C source with explicit int32_t operations and overflow checks.
    """
    report = inspect_backend_readiness(function, "c")
    if not report.ready_for_adapter:
        details = "; ".join(f"{item.feature}: {item.reason}" for item in report.issues)
        raise QIRCBackendError(f"Unsupported QIR for C adapter: {details}")

    # Use generated names rather than interpolating user-controlled identifiers.
    # The public function name is intentionally restricted to C identifiers.
    if not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", function.name):
        raise QIRCBackendError("Function name is not a valid C identifier")
    if function.name.startswith("__") or (function.name.startswith("_") and len(function.name) > 1 and function.name[1].isupper()):
        raise QIRCBackendError("Function name is reserved in C")
    if function.name in {"int", "return", "void", "static", "if", "while", "for", "switch", "typedef", "struct", "union", "enum", "signed", "unsigned", "char", "float", "double", "long", "short", "const", "volatile", "restrict", "inline", "extern", "auto", "register", "break", "continue", "default", "do", "else", "goto", "sizeof", "case", "_Bool", "_Complex", "_Imaginary"}:
        raise QIRCBackendError("Function name is a C keyword")

    identifiers: dict[str, str] = {}
    def name(value):
        if value.name not in identifiers:
            identifiers[value.name] = f"qv_{len(identifiers)}"
        return identifiers[value.name]

    args = ", ".join(f"int32_t {name(param)}" for param in function.parameters) or "void"
    lines = ["#include <stdint.h>", "#include <limits.h>", "#include <stdlib.h>", "", f"int32_t {function.name}({args}) {{"]
    for instruction in function.blocks[0].instructions:
        op = instruction.opcode
        dest = name(instruction.result)
        if op == "const":
            expression = f"INT32_C({instruction.immediate})" if instruction.immediate >= 0 else f"(-INT32_C({-instruction.immediate - 1}) - 1)"
            lines.append(f"    int32_t {dest} = {expression};")
        elif op == "copy":
            lines.append(f"    int32_t {dest} = {name(instruction.operands[0])};")
        elif op in {"add", "sub", "mul"}:
            left, right = (name(item) for item in instruction.operands)
            symbol = {"add": "+", "sub": "-", "mul": "*"}[op]
            # Evaluate in int64_t, then trap on overflow rather than invoke signed C UB.
            lines.append(f"    int64_t tmp_{dest} = (int64_t){left} {symbol} (int64_t){right};")
            lines.append(f"    if (tmp_{dest} < INT32_MIN || tmp_{dest} > INT32_MAX) abort();")
            lines.append(f"    int32_t {dest} = (int32_t)tmp_{dest};")
        else:
            raise QIRCBackendError(f"Unsupported operation: {op}")
    terminator = function.blocks[0].terminator
    if not isinstance(terminator, QReturn) or terminator.value is None:
        raise QIRCBackendError("Expected value return")
    lines.append(f"    return {name(terminator.value)};")
    lines.append("}")
    return "\n".join(lines) + "\n"
