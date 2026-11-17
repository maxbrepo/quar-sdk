"""Strict, opt-in bridge from the existing executable IR to canonical QIR.

Only straight-line, explicitly typed integer functions are supported. Unsupported
nodes fail closed: the existing IR and its backends remain the default pipeline.
"""
from __future__ import annotations

from ..ir.model import (IRArrayGet, IRArrayNew, IRArraySet, IRAssign, IRBinary, IRDeclare, IRFunctionDefinition,
                        IRBoolean, IRString, IRCall, IRWhile, IRFor, IRLoop, IRBreak, IRContinue, IRIf, IRLiteral, IRReference, IRReturn, IRUnary, IRSwitch, IRSwitchCase, IRMatch)
from .array_layout import analyze_array_layout, QIRArrayLayoutError
from .model import QMetadata, QSafetyMetadata
from .enum_binding_plan import plan_match_bindings
from .enum_match_rewrite import rewrite_match_arm
from .enum_layout import QEnumLayout, QIREnumLayoutError
from .model import QBlock, QBranch, QFunction, QInstruction, QJump, QPhi, QReturn, QType, QValue
from .types import is_integer
from .type_normalization import normalize_ir_type, QIRTypeNormalizationError
from .validation import validate_function


class QIRBridgeError(ValueError):
    """The legacy IR construct cannot yet be represented without semantic loss."""


_COMPARISONS = {"==": "eq", "!=": "ne", "<": "lt", "<=": "le", ">": "gt", ">=": "ge"}
_BINARY = {"+": "add", "-": "sub", "*": "mul", "/": "div", "%": "mod", "&": "bit_and", "|": "bit_or", "^": "bit_xor", "<<": "shl", ">>": "shr"}


def lower_ir_function(
    function: IRFunctionDefinition, *, type_aliases: dict[str, str] | None = None,
    enum_layout: QEnumLayout | None = None
) -> QFunction:
    """Lower a straight-line integer IR function, validating the resulting QIR.

    Returns an immutable QFunction. Does not change or execute the legacy IR.
    """
    if not isinstance(function, IRFunctionDefinition):
        raise QIRBridgeError("Expected an executable IRFunctionDefinition")
    if not function.name:
        raise QIRBridgeError("Function name cannot be empty")

    def integer_type(name: str) -> QType:
        try:
            result = normalize_ir_type(name, type_aliases)
        except (QIRTypeNormalizationError, AttributeError, TypeError) as exc:
            raise QIRBridgeError(f"Unsupported IR type: {name!r}") from exc
        if not is_integer(result):
            raise QIRBridgeError(f"Bridge supports integer types only: {name!r}")
        return result

    def value_type(name: str) -> QType:
        return QType("bool") if name == "bool" else QType("string") if name == "string" else integer_type(name)

    return_type = value_type(function.return_type)
    parameters = []
    environment: dict[str, QValue] = {}
    instructions: list[QInstruction] = []
    serial = 0
    for name, type_name, default in function.parameters:
        if default is not None:
            raise QIRBridgeError("Default parameters are not supported by the bridge")
        if not name or name in environment:
            raise QIRBridgeError("Duplicate or empty parameter name")
        value = QValue(name, value_type(type_name))
        parameters.append(value)
        environment[name] = value

    def fresh(qtype: QType) -> QValue:
        nonlocal serial
        serial += 1
        while f"$bridge{serial}" in environment:
            serial += 1
        return QValue(f"$bridge{serial}", qtype)

    pending_phis: list[QPhi] = []
    blocks: list[QBlock] = []
    current_label = "entry"
    block_serial = 0

    def next_label(prefix: str) -> str:
        nonlocal block_serial
        block_serial += 1
        return f"{prefix}_{block_serial}"

    def close_block(terminator: QReturn | QJump | QBranch, *, phis: tuple[QPhi, ...] = ()) -> None:
        nonlocal instructions
        blocks.append(QBlock(current_label, tuple(instructions), terminator, tuple(pending_phis) + phis))
        pending_phis.clear()
        instructions = []

    def typed_integer_candidates(node: object) -> list[QType]:
        """Find explicit integer operand types inside nested arithmetic expressions."""
        if isinstance(node, IRCall) and node.symbol in ("__qir_utf8_scalar_len", "__qir_utf8_scalar_at"):
            # Both internal Unicode scalar intrinsics have a canonical i32 result.
            return [QType("i32")]
        if isinstance(node, IRReference):
            value = environment.get(node.name)
            return [value.type] if value is not None and is_integer(value.type) else []
        if isinstance(node, IRBinary):
            if node.operator in _BINARY:
                return typed_integer_candidates(node.left) + typed_integer_candidates(node.right)
        return []

    def expression(node: object, expected: QType) -> QValue:
        nonlocal current_label
        if isinstance(node, IRCall) and node.symbol in ("__qir_utf8_scalar_len", "__qir_utf8_scalar_at"):
            # Internal opt-in intrinsics; not a public Visual Quar syntax contract.
            operation = "string_scalar_len" if node.symbol.endswith("_len") else "string_scalar_at"
            required = 1 if operation == "string_scalar_len" else 2
            if expected != QType("i32") or len(node.arguments) != required:
                raise QIRBridgeError("Unicode scalar intrinsic requires i32 result and exact arity")
            text_value = expression(node.arguments[0], QType("string"))
            operands = (text_value,)
            if required == 2:
                operands += (expression(node.arguments[1], QType("i32")),)
            checks = ("string_length", "bounds") if required == 2 else ("string_length",)
            result = fresh(QType("i32"))
            instructions.append(QInstruction(operation, operands, result,
                                             metadata=QMetadata(safety=QSafetyMetadata(checks=checks))))
            return result
        if isinstance(node, IRString) and expected.name == "string":
            result = fresh(expected)
            instructions.append(QInstruction("string_const", (), result, node.value))
            return result
        if isinstance(node, IRArrayGet):
            if node.name not in arrays or node.second_index is not None or expected != QType("i32"):
                raise QIRBridgeError("Unsupported array access or element type")
            index = expression(node.index, QType("i32"))
            result = fresh(QType("i32"))
            instructions.append(QInstruction("array_get", (arrays[node.name], index), result, metadata=array_bounds))
            return result
        if isinstance(node, IRBoolean):
            if expected.name != "bool":
                raise QIRBridgeError("Boolean literal requires bool")
            value = fresh(expected)
            instructions.append(QInstruction("const", (), value, node.value))
            return value
        if isinstance(node, IRLiteral) and type(node.value) is int:
            if expected.name == "bool":
                raise QIRBridgeError("Integer literal cannot implicitly become bool")
            value = fresh(expected)
            instructions.append(QInstruction("const", (), value, node.value))
            return value
        if isinstance(node, IRReference):
            if node.name not in environment:
                raise QIRBridgeError(f"Unknown IR reference: {node.name!r}")
            value = environment[node.name]
            if value.type != expected:
                raise QIRBridgeError("Implicit type conversion is not supported")
            return value
        if isinstance(node, IRBinary) and node.operator.lower() in ("and", "or"):
            if expected.name != "bool":
                raise QIRBridgeError("Logical operators require bool operands and result")
            left = expression(node.left, expected)
            left_label = current_label
            rhs_label = next_label("logical_rhs")
            merge_label = next_label("logical_merge")
            is_and = node.operator.lower() == "and"
            close_block(QBranch(left, rhs_label if is_and else merge_label,
                                merge_label if is_and else rhs_label))
            current_label = rhs_label
            right = expression(node.right, expected)
            right_label = current_label
            close_block(QJump(merge_label))
            current_label = merge_label
            result = fresh(expected)
            # The skipped edge retains the left operand; the evaluated edge uses the right.
            pending_phis.append(QPhi(result, ((left_label, left), (right_label, right))))
            return result
        if isinstance(node, IRBinary) and node.operator in _COMPARISONS:
            if expected.name != "bool":
                raise QIRBridgeError("Comparison requires a bool result")
            candidates = typed_integer_candidates(node.left) + typed_integer_candidates(node.right)
            if not candidates or any(t != candidates[0] for t in candidates) or not is_integer(candidates[0]):
                raise QIRBridgeError("Comparison requires compatible typed integer operands")
            left = expression(node.left, candidates[0])
            right = expression(node.right, candidates[0])
            result = fresh(expected)
            instructions.append(QInstruction(_COMPARISONS[node.operator], (left, right), result))
            return result
        if isinstance(node, IRBinary) and node.operator in _BINARY:
            left = expression(node.left, expected)
            right = expression(node.right, expected)
            value = fresh(expected)
            instructions.append(QInstruction(_BINARY[node.operator], (left, right), value))
            return value
        if isinstance(node, IRUnary) and node.operator in ("!", "not", "NOT"):
            if expected.name != "bool":
                raise QIRBridgeError("Logical NOT requires bool")
            operand = expression(node.operand, expected)
            value = fresh(expected)
            instructions.append(QInstruction("logical_not", (operand,), value))
            return value
        if isinstance(node, IRUnary) and node.operator == "~":
            operand = expression(node.operand, expected)
            value = fresh(expected)
            instructions.append(QInstruction("bit_not", (operand,), value))
            return value
        raise QIRBridgeError(f"Unsupported IR expression: {type(node).__name__}")

    arrays: dict[str, QValue] = {}
    array_bounds = QMetadata(safety=QSafetyMetadata(checks=("bounds",)))

    loop_stack: list[dict[str, object]] = []

    def lower_statements(statements: tuple[object, ...], *, top_level: bool = False) -> bool:
        """Lower IR statements and merge SSA environments at conditional joins."""
        nonlocal current_label
        for index, statement in enumerate(statements):
            if isinstance(statement, IRArrayNew):
                if not top_level or statement.name in arrays or statement.name in environment:
                    raise QIRBridgeError("Array declarations require a unique top-level local name")
                try:
                    layout = analyze_array_layout(statement)
                except QIRArrayLayoutError as exc:
                    raise QIRBridgeError(str(exc)) from exc
                pointer = fresh(QType("ptr<i32>"))
                arrays[layout.name] = pointer
                instructions.append(QInstruction("array_alloc", result=pointer, immediate=layout.length))
                for offset, initial in enumerate(layout.initial_values):
                    index = expression(IRLiteral(offset), QType("i32"))
                    value = expression(IRLiteral(initial), QType("i32"))
                    instructions.append(QInstruction("array_set", (pointer, index, value), metadata=array_bounds))
            elif isinstance(statement, IRArraySet):
                if statement.name not in arrays or statement.second_index is not None:
                    raise QIRBridgeError("Unsupported array assignment")
                index = expression(statement.index, QType("i32"))
                value = expression(statement.value, QType("i32"))
                instructions.append(QInstruction("array_set", (arrays[statement.name], index, value), metadata=array_bounds))
            elif isinstance(statement, IRDeclare):
                if not top_level:
                    raise QIRBridgeError("Branch-local declarations are not supported yet")
                if not statement.name or statement.name in environment:
                    raise QIRBridgeError("Duplicate or empty local declaration")
                qtype = value_type(statement.type_name)
                environment[statement.name] = expression(statement.value, qtype)
            elif isinstance(statement, IRAssign):
                if statement.name not in environment:
                    raise QIRBridgeError(f"Assignment to undeclared name: {statement.name!r}")
                environment[statement.name] = expression(statement.value, environment[statement.name].type)
            elif isinstance(statement, IRFor):
                comparison = statement.comparison
                if (statement.counter_name not in environment
                        or not is_integer(environment[statement.counter_name].type)
                        or not isinstance(comparison, IRBinary)
                        or not isinstance(comparison.left, IRReference)
                        or comparison.left.name != statement.counter_name
                        or comparison.operator not in ("<", "<=", ">", ">=")):
                    raise QIRBridgeError("For requires a declared integer counter and a canonical comparison")
                direction = 1 if comparison.operator in ("<", "<=") else -1
                if (type(statement.step) is not int or statement.step <= 0
                        or statement.direction not in (0, direction)):
                    raise QIRBridgeError("For step or direction is invalid")
                update = IRAssign(statement.counter_name, IRBinary(
                    "+" if direction == 1 else "-", IRReference(statement.counter_name),
                    IRLiteral(statement.step)))
                def rewrite_for_continues(items):
                    # Keep the counter update on every for-owned continue edge.
                    # Transfers inside nested loops belong to those loops.
                    rewritten = []
                    for item in items:
                        if isinstance(item, IRContinue):
                            rewritten.extend((update, item))
                        elif isinstance(item, IRIf):
                            rewritten.append(IRIf(item.condition,
                                tuple(rewrite_for_continues(item.then_body)),
                                tuple(rewrite_for_continues(item.else_body))))
                        else:
                            rewritten.append(item)
                    return rewritten

                lowered = (IRAssign(statement.counter_name, statement.start),
                           IRWhile(comparison, tuple(rewrite_for_continues(statement.body)) + (() if any(isinstance(item, (IRBreak, IRContinue, IRReturn)) for item in statement.body) else (update,))))
                return lower_statements(lowered + tuple(statements[index + 1:]), top_level=top_level)
            elif isinstance(statement, IRLoop):
                # Lower explicit infinite loops through the shared while CFG.
                return lower_statements(
                    (IRWhile(IRBoolean(True), statement.body),) + tuple(statements[index + 1:]),
                    top_level=top_level)
            elif isinstance(statement, (IRBreak, IRContinue)):
                if not loop_stack:
                    raise QIRBridgeError("Loop transfer outside a supported loop")
                # A transfer ends this path; trailing statements are unreachable.
                context = loop_stack[-1]
                is_break = isinstance(statement, IRBreak)
                destination = context["exit"] if is_break else context["header"]
                edge_list = context["break_edges"] if is_break else context["continue_edges"]
                edge_list.append((current_label, dict(environment)))
                close_block(QJump(destination))
                return True
            elif isinstance(statement, IRWhile):
                # A conservative first subset: assignments and conditional
                # assignments, without early returns or loop transfers.
                def changed_names(items):
                    names = set()
                    for item in items:
                        if isinstance(item, IRAssign):
                            names.add(item.name)
                        elif isinstance(item, IRArraySet):
                            # Indexed writes mutate storage, not the scalar SSA environment.
                            pass
                        elif isinstance(item, IRReturn):
                            # Ignore all unreachable writes after an unconditional return.
                            break
                        elif isinstance(item, (IRBreak, IRContinue)):
                            break
                        elif isinstance(item, IRIf):
                            names.update(changed_names(item.then_body))
                            names.update(changed_names(item.else_body))
                        elif isinstance(item, IRLoop):
                            names.update(changed_names(item.body))
                        elif isinstance(item, IRWhile):
                            names.update(changed_names(item.body))
                        elif isinstance(item, IRFor):
                            # A nested counter loop initializes and updates its counter.
                            names.add(item.counter_name)
                            names.update(changed_names(item.body))
                        else:
                            raise QIRBridgeError("While body supports assignments and if statements only")
                    return names

                # Branch-local transfers are handled by the existing If lowering:
                # terminated branches do not contribute an edge to the join.
                # Their snapshots are recorded as loop break/continue edges.
                modified = changed_names(statement.body)
                if any(name not in environment for name in modified):
                    raise QIRBridgeError("While assigns an undeclared variable")
                before = dict(environment)
                preheader = current_label
                header = next_label("while_header")
                body_label = next_label("while_body")
                exit_label = next_label("while_exit")
                close_block(QJump(header))
                current_label = header
                loop_phis = {name: fresh(before[name].type) for name in sorted(modified)}
                environment.update(loop_phis)
                header_index = len(blocks)
                condition = expression(statement.condition, QType("bool"))
                close_block(QBranch(condition, body_label, exit_label))
                current_label = body_label
                context = {"header": header, "exit": exit_label, "break_edges": [], "continue_edges": []}
                loop_stack.append(context)
                try:
                    terminated = lower_statements(statement.body)
                finally:
                    loop_stack.pop()
                back_edges = list(context["continue_edges"])
                if not terminated:
                    back_edges.append((current_label, dict(environment)))
                    close_block(QJump(header))
                header_block = blocks[header_index]
                phis = tuple(QPhi(loop_phis[name], tuple(
                    [(preheader, before[name])] +
                    [(label, snapshot[name]) for label, snapshot in back_edges]))
                    for name in sorted(modified))
                blocks[header_index] = QBlock(header_block.label, header_block.instructions,
                                              header_block.terminator, phis + header_block.phis)
                current_label = exit_label
                environment.clear()
                environment.update(before)
                environment.update(loop_phis)
                break_edges = context["break_edges"]
                if break_edges:
                    # Merge normal condition-false exit with each early break.
                    for name in sorted(modified):
                        sources = [(header, loop_phis[name])] + [
                            (label, snapshot[name]) for label, snapshot in break_edges]
                        if len(set(value for _, value in sources)) > 1:
                            merged = fresh(before[name].type)
                            pending_phis.append(QPhi(merged, tuple(sources)))
                            environment[name] = merged
            elif isinstance(statement, IRMatch):
                if enum_layout is None:
                    raise QIRBridgeError("IRMatch requires an enum layout")
                if not isinstance(statement.expression, IRReference) or statement.expression.name not in environment or environment[statement.expression.name].type != QType("i32"):
                    raise QIRBridgeError("IRMatch requires an i32 tag parameter or variable")
                if not statement.default_body:
                    raise QIRBridgeError("IRMatch requires an explicit default for invalid tags")
                try:
                    plans = plan_match_bindings(enum_layout, statement.arms)
                    cases = [IRSwitchCase(IRLiteral(plan.tag), rewrite_match_arm(arm.body, plan, {key: value.type for key, value in environment.items()}, legacy=True))
                             for arm, plan in zip(statement.arms, plans)]
                except QIREnumLayoutError as exc:
                    raise QIRBridgeError(str(exc)) from exc
                return lower_statements((IRSwitch(statement.expression, tuple(cases), statement.default_body),) + tuple(statements[index + 1:]), top_level=top_level)
            elif isinstance(statement, IRSwitch):
                if not isinstance(statement.expression, (IRReference, IRLiteral)):
                    raise QIRBridgeError("IRSwitch requires a reference or integer literal scrutinee")
                if not statement.cases:
                    return lower_statements(tuple(statement.default_body) + tuple(statements[index + 1:]),
                                            top_level=top_level)
                tail = tuple(statement.default_body)
                for case in reversed(statement.cases):
                    if not isinstance(case.value, IRLiteral) or type(case.value.value) is not int:
                        raise QIRBridgeError("IRSwitch supports integer literal cases only")
                    tail = (IRIf(IRBinary("==", statement.expression, case.value),
                                 tuple(case.body), tail),)
                return lower_statements(tail + tuple(statements[index + 1:]), top_level=top_level)
            elif isinstance(statement, IRIf):
                condition = expression(statement.condition, QType("bool"))
                then_label = next_label("if_then")
                else_label = next_label("if_else")
                join_label = next_label("if_join")
                close_block(QBranch(condition, then_label, else_label))
                incoming = dict(environment)

                current_label = then_label
                environment.clear()
                environment.update(incoming)
                then_return = lower_statements(statement.then_body)
                then_exit = current_label
                then_values = dict(environment)
                if not then_return:
                    close_block(QJump(join_label))

                current_label = else_label
                environment.clear()
                environment.update(incoming)
                else_return = lower_statements(statement.else_body)
                else_exit = current_label
                else_values = dict(environment)
                if not else_return:
                    close_block(QJump(join_label))

                if then_return and else_return:
                    return True
                current_label = join_label
                environment.clear()
                if then_return or else_return:
                    environment.update(else_values if then_return else then_values)
                else:
                    for name, original in incoming.items():
                        left, right = then_values[name], else_values[name]
                        if left == right:
                            environment[name] = left
                        else:
                            merged = fresh(original.type)
                            pending_phis.append(QPhi(merged, ((then_exit, left), (else_exit, right))))
                            environment[name] = merged
            elif isinstance(statement, IRReturn):
                # Preserve the same unreachable-tail semantics as AST lowering.
                close_block(QReturn(expression(statement.value, return_type)))
                return True
            else:
                raise QIRBridgeError(f"Unsupported IR statement: {type(statement).__name__}")
        return False

    terminated = lower_statements(function.body, top_level=True)
    if not terminated:
        raise QIRBridgeError("A final return statement is required")
    result = QFunction(function.name, return_type, tuple(parameters), tuple(blocks))
    try:
        validate_function(result)
    except ValueError as exc:
        raise QIRBridgeError(f"Generated QIR failed validation: {exc}") from exc
    return result
