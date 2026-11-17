"""C99 module emission for validated i32 QIR functions and direct calls.

This deliberately narrow adapter rejects non-i32 signatures and call cycles.
"""
from __future__ import annotations

import re

from .c_backend import QIRCBackendError, emit_c_function
from .model import QModule
from .validation import validate_module


def emit_c_module(module: QModule) -> str:
    """Return a single C99 translation unit for validated i32 functions."""
    validate_module(module)
    functions = {function.name: function for function in module.functions}
    if not functions:
        raise QIRCBackendError("Empty QIR module")
    for function in module.functions:
        if function.return_type.name != "i32" or any(p.type.name != "i32" for p in function.parameters):
            raise QIRCBackendError("Module C adapter supports i32 signatures only")
        if not re.fullmatch(r"[A-Za-z][A-Za-z_0-9]*", function.name):
            raise QIRCBackendError("Module function name is not a safe C identifier")
    symbols = frozenset(functions)
    declarations = []
    bodies = []
    for function in module.functions:
        args = ", ".join("int32_t " + "qv_" + str(i) for i, _ in enumerate(function.parameters)) or "void"
        declaration = f"int32_t {function.name}({args})"
        source = emit_c_function(function, call_symbols=symbols)
        start = source.find(declaration + " {")
        if start < 0:
            raise QIRCBackendError("Unable to isolate generated function body")
        # Module subset forbids string operations, whose helpers need a shared prelude.
        if any(instruction.opcode.startswith("string_") for block in function.blocks for instruction in block.instructions):
            raise QIRCBackendError("String operations not supported in module adapter")
        declarations.append(declaration + ";")
        bodies.append(source[start:])
    return "#include <stdint.h>\n#include <limits.h>\n#include <stdlib.h>\n\n" + "\n".join(declarations) + "\n\n" + "\n".join(bodies)
