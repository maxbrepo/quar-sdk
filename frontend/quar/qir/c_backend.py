"""Small, executable C99 adapter for the validated QIR i32 subset.

This adapter does not replace the legacy C backend or discharge safety checks.
"""
from __future__ import annotations

import re

from .backend_readiness import inspect_backend_readiness
from .cast_safety import assess_integer_cast
from .model import QBranch, QFunction, QJump, QReturn


class QIRCBackendError(ValueError):
    """Raised when QIR cannot be safely lowered to the initial C subset."""


def emit_c_function(function: QFunction, *, call_symbols: frozenset[str] = frozenset()) -> str:
    """Emit a standalone C99 function for the supported, validated QIR subset.

    Returns C source with explicit int32_t operations and overflow checks.
    """
    report = inspect_backend_readiness(function, "c")
    issues = tuple(item for item in report.issues if not (call_symbols and item.feature == "opcode" and item.reason == "Unsupported adapter opcode: call"))
    if issues:
        details = "; ".join(f"{item.feature}: {item.reason}" for item in issues)
        raise QIRCBackendError(f"Unsupported QIR for C adapter: {details}")

    allocated = {instr.result.name for block in function.blocks for instr in block.instructions if instr.opcode == "array_alloc"}
    for block in function.blocks:
        for phi in block.phis:
            if phi.result.type.name == "ptr<i32>":
                raise QIRCBackendError("Array pointer phi is not supported")
        for instr in block.instructions:
            if instr.opcode in {"array_get", "array_set"} and instr.operands[0].name not in allocated:
                raise QIRCBackendError("Array access requires a direct local allocation")
            if instr.opcode == "copy" and instr.result.type.name == "ptr<i32>":
                raise QIRCBackendError("Array pointer copy is not supported")
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

    def c_type(value):
        return {"bool": "_Bool", "i8": "int8_t", "u8": "uint8_t", "i16": "int16_t", "u16": "uint16_t", "i32": "int32_t", "ptr<i32>": "int32_t *", "string": "qir_string"}[value.type.name]

    return_c_type = {"bool": "_Bool", "i8": "int8_t", "u8": "uint8_t", "i16": "int16_t", "u16": "uint16_t", "i32": "int32_t", "string": "qir_string"}[function.return_type.name]
    args = ", ".join(f"{c_type(param)} {name(param)}" for param in function.parameters) or "void"
    lines = ["#include <stdint.h>", "#include <stddef.h>", "#include <limits.h>", "#include <stdlib.h>", "", "typedef struct { const uint8_t *data; size_t length; } qir_string;", "", "static int32_t qir_utf8_scalar_len(qir_string text) {", "    if (text.length > INT32_MAX || (text.length != 0 && text.data == NULL)) abort();", "    size_t index = 0;", "    int32_t count = 0;", "    while (index < text.length) {", "        uint8_t lead = text.data[index];", "        uint32_t scalar;", "        size_t width;", "        if (lead < 0x80) { scalar = lead; width = 1; }", "        else if (lead >= 0xC2 && lead <= 0xDF) { scalar = lead & 0x1F; width = 2; }", "        else if (lead >= 0xE0 && lead <= 0xEF) { scalar = lead & 0x0F; width = 3; }", "        else if (lead >= 0xF0 && lead <= 0xF4) { scalar = lead & 0x07; width = 4; }", "        else abort();", "        if (width > text.length - index) abort();", "        for (size_t j = 1; j < width; ++j) {", "            uint8_t tail = text.data[index + j];", "            if ((tail & 0xC0) != 0x80) abort();", "            scalar = (scalar << 6) | (tail & 0x3F);", "        }", "        if ((width == 2 && scalar < 0x80) ||", "            (width == 3 && scalar < 0x800) ||", "            (width == 4 && scalar < 0x10000) ||", "            (scalar >= 0xD800 && scalar <= 0xDFFF) || scalar > 0x10FFFF) abort();", "        index += width;", "        ++count;", "    }", "    return count;", "}", "", f"{return_c_type} {function.name}({args}) {{"]
    if any(instr.opcode == "string_scalar_at" for block in function.blocks for instr in block.instructions):
        # Decode the requested scalar by reusing the validated UTF-8 traversal.
        helper = [
            "static int32_t qir_utf8_scalar_at(qir_string text, int32_t position) {",
            "    if (position < 0 || text.length > INT32_MAX || (text.length && !text.data)) abort();",
            "    size_t index = 0;",
            "    int32_t current = 0;",
            "    while (index < text.length) {",
            "        uint8_t lead = text.data[index];",
            "        uint32_t scalar; size_t width;",
            "        if (lead < 0x80) { scalar = lead; width = 1; }",
            "        else if (lead >= 0xC2 && lead <= 0xDF) { scalar = lead & 0x1F; width = 2; }",
            "        else if (lead >= 0xE0 && lead <= 0xEF) { scalar = lead & 0x0F; width = 3; }",
            "        else if (lead >= 0xF0 && lead <= 0xF4) { scalar = lead & 0x07; width = 4; }",
            "        else abort();",
            "        if (width > text.length - index) abort();",
            "        for (size_t j = 1; j < width; ++j) {",
            "            uint8_t tail = text.data[index + j];",
            "            if ((tail & 0xC0) != 0x80) abort();",
            "            scalar = (scalar << 6) | (tail & 0x3F);",
            "        }",
            "        if ((width == 2 && scalar < 0x80) || (width == 3 && scalar < 0x800) ||",
            "            (width == 4 && scalar < 0x10000) ||",
            "            (scalar >= 0xD800 && scalar <= 0xDFFF) || scalar > 0x10FFFF) abort();",
            "        if (current == position) return (int32_t)scalar;",
            "        index += width; ++current;",
            "    }",
            "    abort();",
            "}", ""
        ]
        lines[lines.index(f"{return_c_type} {function.name}({args}) {{"):lines.index(f"{return_c_type} {function.name}({args}) {{")] = helper
    # Array capacities are derived from allocation instructions, never from pointer values.
    capacities = {}
    for block in function.blocks:
        for instr in block.instructions:
            if instr.opcode == "array_alloc":
                capacities[instr.result.name] = instr.immediate
    # Avoid unused-function warnings in C builds that use -Werror.
    if not any(instr.opcode == "string_scalar_len" for block in function.blocks for instr in block.instructions):
        start = lines.index("static int32_t qir_utf8_scalar_len(qir_string text) {")
        end = lines.index("}", start)
        del lines[start:end + 2]
    # Declare SSA values once, at function scope, so branches can share them.
    for block in function.blocks:
        for phi in block.phis:
            lines.append(f"    {c_type(phi.result)} {name(phi.result)};")
        for instruction in block.instructions:
            if instruction.result is not None:
                lines.append(f"    {c_type(instruction.result)} {name(instruction.result)};")
    # Taking the address is valid C99 and prevents -Wunused-but-set-variable
    # for SSA definitions superseded by later source assignments. It does not
    # read an uninitialized value and is optimized away by C compilers.
    for block in function.blocks:
        for instruction in block.instructions:
            if instruction.result is not None:
                lines.append(f"    (void)&{name(instruction.result)};")
        for phi in block.phis:
            lines.append(f"    (void)&{name(phi.result)};")
    labels = {block.label: f"qb_{index}" for index, block in enumerate(function.blocks)}
    lines.append(f"    goto {labels[function.blocks[0].label]};")
    for block in function.blocks:
        lines.append(f"{labels[block.label]}:;")
        for instruction in block.instructions:
            op = instruction.opcode
            dest = name(instruction.result) if instruction.result is not None else None
            if op == "call":
                if instruction.immediate not in call_symbols or dest is None:
                    raise QIRCBackendError("Call target is not a validated module function")
                arguments = ", ".join(name(value) for value in instruction.operands)
                lines.append(f"    {dest} = {instruction.immediate}({arguments});")
            elif op == "string_const":
                encoded = instruction.immediate.encode("utf-8")
                # C99 does not permit empty initializer arrays; use a dummy byte.
                content = ", ".join(str(byte) for byte in encoded) if encoded else "0"
                lines.append(f"    static const uint8_t data_{dest}[] = {{{content}}};")
                lines.append(f"    {dest} = (qir_string){{data_{dest}, {len(encoded)}}};")
            elif op in {"string_byte_len", "string_scalar_len"}:
                source = name(instruction.operands[0])
                if op == "string_byte_len":
                    lines.append(f"    if ({source}.length > INT32_MAX || ({source}.length != 0 && {source}.data == NULL)) abort();")
                    lines.append(f"    {dest} = (int32_t){source}.length;")
                else:
                    lines.append(f"    {dest} = qir_utf8_scalar_len({source});")
            elif op == "string_scalar_at":
                lines.append(f"    {dest} = qir_utf8_scalar_at({name(instruction.operands[0])}, {name(instruction.operands[1])});")
            elif op == "array_alloc":
                lines.append(f"    int32_t storage_{dest}[{instruction.immediate}] = {{0}};")
                lines.append(f"    {dest} = storage_{dest};")
            elif op in {"array_get", "array_set"}:
                pointer, index = instruction.operands[:2]
                if pointer.name not in capacities:
                    raise QIRCBackendError("Array access requires a direct local array allocation")
                # Abort before the C subscript is evaluated; no unchecked pointer arithmetic.
                lines.append(f"    if ({name(index)} < 0 || {name(index)} >= {capacities[pointer.name]}) abort();")
                if op == "array_get":
                    lines.append(f"    {dest} = {name(pointer)}[{name(index)}];")
                else:
                    lines.append(f"    {name(pointer)}[{name(index)}] = {name(instruction.operands[2])};")
            elif op == "const":
                if instruction.result.type.name == "bool":
                    lines.append(f"    {dest} = {1 if instruction.immediate else 0};")
                else:
                    expression = f"INT32_C({instruction.immediate})" if instruction.immediate >= 0 else f"(-INT32_C({-instruction.immediate - 1}) - 1)"
                    lines.append(f"    {dest} = {expression};")
            elif op == "cast":
                source = instruction.operands[0]
                assessment = assess_integer_cast(source.type, instruction.result.type)
                source_name = name(source)
                if assessment.requires_runtime_check:
                    lines.append(f"    if ((int64_t){source_name} < {assessment.minimum} || (int64_t){source_name} > {assessment.maximum}) abort();")
                lines.append(f"    {dest} = ({c_type(instruction.result)}){source_name};")
            elif op == "copy":
                lines.append(f"    {dest} = {name(instruction.operands[0])};")
            elif op in {"add", "sub", "mul"}:
                left, right = (name(item) for item in instruction.operands)
                symbol = {"add": "+", "sub": "-", "mul": "*"}[op]
                # Evaluate in int64_t, then trap on overflow rather than invoke signed C UB.
                lines.append(f"    int64_t tmp_{dest} = (int64_t){left} {symbol} (int64_t){right};")
                lines.append(f"    if (tmp_{dest} < INT32_MIN || tmp_{dest} > INT32_MAX) abort();")
                lines.append(f"    {dest} = (int32_t)tmp_{dest};")
            elif op in {"div", "mod"}:
                left, right = (name(item) for item in instruction.operands)
                # Guard both undefined C integer cases before evaluating the expression.
                lines.append(f"    if ({right} == 0 || ({left} == INT32_MIN && {right} == -1)) abort();")
                symbol = "/" if op == "div" else "%"
                lines.append(f"    {dest} = {left} {symbol} {right};")
            elif op in {"eq", "ne", "lt", "le", "gt", "ge"}:
                left, right = (name(item) for item in instruction.operands)
                symbol = {"eq": "==", "ne": "!=", "lt": "<", "le": "<=", "gt": ">", "ge": ">="}[op]
                lines.append(f"    {dest} = {left} {symbol} {right};")
            elif op == "logical_not":
                lines.append(f"    {dest} = !{name(instruction.operands[0])};")
            elif op in {"bit_and", "bit_or", "bit_xor", "bit_not", "shl", "shr"}:
                left = name(instruction.operands[0])
                if op == "bit_not":
                    bits = f"(~(uint32_t){left})"
                elif op in {"bit_and", "bit_or", "bit_xor"}:
                    right = name(instruction.operands[1])
                    symbol = {"bit_and": "&", "bit_or": "|", "bit_xor": "^"}[op]
                    bits = f"((uint32_t){left} {symbol} (uint32_t){right})"
                else:
                    right = name(instruction.operands[1])
                    lines.append(f"    if ({right} < 0 || {right} >= 32) abort();")
                    if op == "shl":
                        bits = f"((uint32_t){left} << (uint32_t){right})"
                    else:
                        # Explicit sign extension; C signed right shift is implementation-defined.
                        bits = f"(((uint32_t){left} >> (uint32_t){right}) | (({left} < 0 && {right} != 0) ? (UINT32_MAX << (32 - (uint32_t){right})) : UINT32_C(0)))"
                # Convert the unsigned bit pattern without implementation-defined casts.
                lines.append(f"    uint32_t bits_{dest} = {bits};")
                lines.append(f"    int64_t signed_{dest} = bits_{dest} <= INT32_MAX ? (int64_t)bits_{dest} : (int64_t)bits_{dest} - INT64_C(4294967296);")
                lines.append(f"    {dest} = (int32_t)signed_{dest};")
            else:
                raise QIRCBackendError(f"Unsupported operation: {op}")
        term = block.terminator
        def edge(target):
            # Read every phi input before updating any phi destination.
            destination = next(item for item in function.blocks if item.label == target)
            incoming = []
            for phi in destination.phis:
                source = next(value for label, value in phi.incoming if label == block.label)
                temp = f"edge_{len(lines)}_{len(incoming)}"
                lines.append(f"    {c_type(phi.result)} {temp} = {name(source)};")
                incoming.append((phi, temp))
            for phi, temp in incoming:
                lines.append(f"    {name(phi.result)} = {temp};")
            lines.append(f"    goto {labels[target]};")
        if isinstance(term, QReturn):
            lines.append(f"    return {name(term.value)};")
        elif isinstance(term, QJump):
            edge(term.target)
        elif isinstance(term, QBranch):
            lines.append(f"    if ({name(term.condition)}) {{")
            edge(term.true_target)
            lines.append("    } else {")
            edge(term.false_target)
            lines.append("    }")
    lines.append("}")
    return "\n".join(lines) + "\n"
