"""Opt-in direct AST-to-QIR lowering for a strictly typed linear integer subset.

This module does not import the legacy IR. Unsupported constructs fail closed.
"""
from __future__ import annotations

from collections.abc import Mapping

from ..ast_nodes import (ArrayAccess, ArrayAssignment, ArrayDeclaration, Assignment, BinaryOperation, Boolean, FunctionCall, FunctionDefinition, WhileStatement, ForStatement, LoopStatement, BreakStatement, ContinueStatement, IfStatement, Integer, SwitchCase, SwitchStatement, MatchStatement,
                         ReturnStatement, UnaryOperation, Variable, VariableDeclaration, String)
from .array_layout import analyze_array_layout, QIRArrayLayoutError
from .model import QMetadata, QSafetyMetadata
from .enum_binding_plan import plan_match_bindings
from .enum_match_rewrite import rewrite_match_arm
from .enum_layout import QEnumLayout, QIREnumLayoutError
from .model import QBlock, QBranch, QFunction, QInstruction, QJump, QPhi, QReturn, QType, QValue
from .type_normalization import QIRTypeNormalizationError, normalize_ir_type
from .types import is_integer
from .validation import validate_function


class QIRASTLoweringError(ValueError):
    """The source AST is outside the verified direct-lowering subset."""


_COMPARISONS = {"==": "eq", "!=": "ne", "<": "lt", "<=": "le", ">": "gt", ">=": "ge"}
_OPERATORS = {"+": "add", "-": "sub", "*": "mul", "/": "div", "%": "mod", "&": "bit_and", "|": "bit_or", "^": "bit_xor", "<<": "shl", ">>": "shr"}


def lower_ast_function(function: FunctionDefinition, *,
                       type_aliases: Mapping[str, str] | None = None,
                       enum_layout: QEnumLayout | None = None) -> QFunction:
    """Lower one linear integer AST function directly to validated immutable QIR.

    The caller is responsible for running semantic analysis first. This
    function also checks its own supported subset, types and definitions.
    Returns a QFunction; it never mutates the AST or the legacy IR pipeline.
    """
    if not isinstance(function, FunctionDefinition) or not isinstance(function.name, str) or not function.name:
        raise QIRASTLoweringError("Expected a named AST FunctionDefinition")

    def integer_type(name: str) -> QType:
        try:
            qtype = normalize_ir_type(name, type_aliases)
        except (QIRTypeNormalizationError, TypeError, AttributeError) as exc:
            raise QIRASTLoweringError(f"Unsupported source type: {name!r}") from exc
        if not is_integer(qtype):
            raise QIRASTLoweringError(f"Direct AST lowering supports integer types only: {name!r}")
        return qtype

    def value_type(name: str) -> QType:
        return QType("bool") if name == "bool" else QType("string") if name == "string" else integer_type(name)

    result_type = value_type(function.return_type)
    params: list[QValue] = []
    values: dict[str, QValue] = {}
    declared_types: dict[str, QType] = {}
    instructions: list[QInstruction] = []
    serial = 0

    def fresh(qtype: QType) -> QValue:
        nonlocal serial
        serial += 1
        return QValue(f"$ast{serial}", qtype)

    for parameter in function.parameters:
        if parameter.default_value is not None:
            raise QIRASTLoweringError("Default parameters are unsupported")
        if not isinstance(parameter.name, str) or not parameter.name or parameter.name in values:
            raise QIRASTLoweringError("Duplicate or empty parameter")
        qtype = value_type(parameter.var_type)
        value = QValue(parameter.name, qtype)
        params.append(value)
        values[parameter.name] = value
        declared_types[parameter.name] = qtype

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
        if isinstance(node, FunctionCall) and node.name in ("__qir_utf8_scalar_len", "__qir_utf8_scalar_at"):
            # Both internal Unicode scalar intrinsics have a canonical i32 result.
            return [QType("i32")]
        if isinstance(node, Variable):
            value = values.get(node.name)
            return [value.type] if value is not None and is_integer(value.type) else []
        if isinstance(node, BinaryOperation):
            if node.operator in _OPERATORS:
                return typed_integer_candidates(node.left) + typed_integer_candidates(node.right)
        return []

    def expression(node: object, expected: QType) -> QValue:
        nonlocal current_label
        if isinstance(node, FunctionCall) and node.name in ("__qir_utf8_scalar_len", "__qir_utf8_scalar_at"):
            # Internal opt-in intrinsics; not a public Visual Quar syntax contract.
            operation = "string_scalar_len" if node.name.endswith("_len") else "string_scalar_at"
            required = 1 if operation == "string_scalar_len" else 2
            if expected != QType("i32") or len(node.arguments) != required:
                raise QIRASTLoweringError("Unicode scalar intrinsic requires i32 result and exact arity")
            text_value = expression(node.arguments[0], QType("string"))
            operands = (text_value,)
            if required == 2:
                operands += (expression(node.arguments[1], QType("i32")),)
            checks = ("string_length", "bounds") if required == 2 else ("string_length",)
            result = fresh(QType("i32"))
            instructions.append(QInstruction(operation, operands, result,
                                             metadata=QMetadata(safety=QSafetyMetadata(checks=checks))))
            return result
        if isinstance(node, String) and expected.name == "string":
            result = fresh(expected)
            instructions.append(QInstruction("string_const", (), result, node.value))
            return result
        if isinstance(node, ArrayAccess):
            if node.name not in arrays or node.second_index is not None or expected != QType("i32"):
                raise QIRASTLoweringError("Unsupported array access or element type")
            index = expression(node.index, QType("i32"))
            result = fresh(QType("i32"))
            instructions.append(QInstruction("array_get", (arrays[node.name], index), result, metadata=array_bounds))
            return result
        if isinstance(node, Boolean) and type(node.value) is bool:
            if expected.name != "bool":
                raise QIRASTLoweringError("Boolean literal requires bool")
            value = fresh(expected)
            instructions.append(QInstruction("const", (), value, node.value))
            return value
        if isinstance(node, Integer) and type(node.value) is int:
            if expected.name == "bool":
                raise QIRASTLoweringError("Integer literal cannot implicitly become bool")
            value = fresh(expected)
            instructions.append(QInstruction("const", (), value, node.value))
            return value
        if isinstance(node, Variable):
            if node.name not in values:
                raise QIRASTLoweringError(f"Undefined variable: {node.name!r}")
            value = values[node.name]
            if value.type != expected:
                raise QIRASTLoweringError("Implicit numeric conversion is unsupported")
            return value
        if isinstance(node, BinaryOperation) and node.operator.lower() in ("and", "or"):
            if expected.name != "bool":
                raise QIRASTLoweringError("Logical operators require bool operands and result")
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
        if isinstance(node, BinaryOperation) and node.operator in _COMPARISONS:
            if expected.name != "bool":
                raise QIRASTLoweringError("Comparison requires a bool result")
            # Infer the operand width from an explicitly typed variable.
            candidates = typed_integer_candidates(node.left) + typed_integer_candidates(node.right)
            if not candidates or any(t != candidates[0] for t in candidates) or not is_integer(candidates[0]):
                raise QIRASTLoweringError("Comparison requires compatible typed integer operands")
            left = expression(node.left, candidates[0])
            right = expression(node.right, candidates[0])
            result = fresh(expected)
            instructions.append(QInstruction(_COMPARISONS[node.operator], (left, right), result))
            return result
        if isinstance(node, BinaryOperation) and node.operator in _OPERATORS:
            left = expression(node.left, expected)
            right = expression(node.right, expected)
            value = fresh(expected)
            instructions.append(QInstruction(_OPERATORS[node.operator], (left, right), value))
            return value
        if isinstance(node, UnaryOperation) and node.operator in ("!", "not", "NOT"):
            if expected.name != "bool":
                raise QIRASTLoweringError("Logical NOT requires bool")
            operand = expression(node.operand, expected)
            value = fresh(expected)
            instructions.append(QInstruction("logical_not", (operand,), value))
            return value
        if isinstance(node, UnaryOperation) and node.operator == "~":
            operand = expression(node.operand, expected)
            value = fresh(expected)
            instructions.append(QInstruction("bit_not", (operand,), value))
            return value
        raise QIRASTLoweringError(f"Unsupported AST expression: {type(node).__name__}")

    arrays: dict[str, QValue] = {}
    array_bounds = QMetadata(safety=QSafetyMetadata(checks=("bounds",)))

    loop_stack: list[dict[str, object]] = []

    def lower_statements(statements: list, *, top_level: bool = False) -> bool:
        """Lower statements while preserving SSA values across conditional edges."""
        nonlocal current_label
        for index, statement in enumerate(statements):
            if isinstance(statement, ArrayDeclaration):
                if not top_level or statement.name in arrays or statement.name in declared_types:
                    raise QIRASTLoweringError("Array declarations require a unique top-level local name")
                try:
                    layout = analyze_array_layout(statement)
                except QIRArrayLayoutError as exc:
                    raise QIRASTLoweringError(str(exc)) from exc
                pointer = fresh(QType("ptr<i32>"))
                arrays[layout.name] = pointer
                instructions.append(QInstruction("array_alloc", result=pointer, immediate=layout.length))
                for offset, initial in enumerate(layout.initial_values):
                    index = expression(Integer(offset), QType("i32"))
                    value = expression(Integer(initial), QType("i32"))
                    instructions.append(QInstruction("array_set", (pointer, index, value), metadata=array_bounds))
            elif isinstance(statement, ArrayAssignment):
                if statement.name not in arrays or statement.second_index is not None:
                    raise QIRASTLoweringError("Unsupported array assignment")
                index = expression(statement.index, QType("i32"))
                value = expression(statement.value, QType("i32"))
                instructions.append(QInstruction("array_set", (arrays[statement.name], index, value), metadata=array_bounds))
            elif isinstance(statement, VariableDeclaration):
                if not top_level:
                    raise QIRASTLoweringError("Branch-local declarations are not supported yet")
                if not isinstance(statement.name, str) or not statement.name or statement.name in declared_types:
                    raise QIRASTLoweringError("Duplicate or empty local declaration")
                qtype = value_type(statement.var_type)
                value = expression(statement.value, qtype)
                declared_types[statement.name] = qtype
                values[statement.name] = value
            elif isinstance(statement, Assignment):
                if statement.name not in declared_types:
                    raise QIRASTLoweringError(f"Assignment to undeclared variable: {statement.name!r}")
                values[statement.name] = expression(statement.value, declared_types[statement.name])
            elif isinstance(statement, ForStatement):
                # Canonical counter loop: initialize once, test before each
                # iteration, then update the counter. Transfers are rejected
                # by the conservative while subset until dedicated CFG support.
                comparison = statement.comparison
                if (statement.counter_name not in declared_types
                        or not is_integer(declared_types[statement.counter_name])
                        or not isinstance(comparison, BinaryOperation)
                        or not isinstance(comparison.left, Variable)
                        or comparison.left.name != statement.counter_name
                        or comparison.operator not in ("<", "<=", ">", ">=")):
                    raise QIRASTLoweringError("For requires a declared integer counter and a canonical comparison")
                direction = 1 if comparison.operator in ("<", "<=") else -1
                if (type(statement.step) is not int or statement.step <= 0
                        or statement.direction not in (0, direction)):
                    raise QIRASTLoweringError("For step or direction is invalid")
                update = Assignment(statement.counter_name, BinaryOperation(
                    Variable(statement.counter_name), "+" if direction == 1 else "-",
                    Integer(statement.step)))
                def rewrite_for_continues(items):
                    # A continue owned by this for must execute its counter update.
                    # Nested loops own their transfers and must remain untouched.
                    rewritten = []
                    for item in items:
                        if isinstance(item, ContinueStatement):
                            rewritten.extend((update, item))
                        elif isinstance(item, IfStatement):
                            rewritten.append(IfStatement(item.condition,
                                rewrite_for_continues(item.then_body),
                                rewrite_for_continues(item.else_body)))
                        else:
                            rewritten.append(item)
                    return rewritten

                lowered = [Assignment(statement.counter_name, statement.start),
                           WhileStatement(comparison, rewrite_for_continues(statement.body) + ([] if any(isinstance(item, (BreakStatement, ContinueStatement, ReturnStatement)) for item in statement.body) else [update]))]
                return lower_statements(lowered + list(statements[index + 1:]), top_level=top_level)
            elif isinstance(statement, LoopStatement):
                # Explicit infinite loop shares the validated while CFG and SSA.
                # Only an owned break can reach the following statement.
                return lower_statements(
                    [WhileStatement(Boolean(True), statement.body)] + list(statements[index + 1:]),
                    top_level=top_level)
            elif isinstance(statement, (BreakStatement, ContinueStatement)):
                if not loop_stack:
                    raise QIRASTLoweringError("Loop transfer outside a supported loop")
                # A transfer ends this path; trailing statements are unreachable.
                context = loop_stack[-1]
                is_break = isinstance(statement, BreakStatement)
                destination = context["exit"] if is_break else context["header"]
                edge_list = context["break_edges"] if is_break else context["continue_edges"]
                edge_list.append((current_label, dict(values)))
                close_block(QJump(destination))
                return True
            elif isinstance(statement, WhileStatement):
                # A conservative first subset: assignments and conditional
                # assignments, without early returns or loop transfers.
                def changed_names(items):
                    names = set()
                    for item in items:
                        if isinstance(item, Assignment):
                            names.add(item.name)
                        elif isinstance(item, ArrayAssignment):
                            # Indexed writes mutate storage, not the scalar SSA environment.
                            pass
                        elif isinstance(item, ReturnStatement):
                            # Ignore all unreachable writes after an unconditional return.
                            break
                        elif isinstance(item, (BreakStatement, ContinueStatement)):
                            break
                        elif isinstance(item, IfStatement):
                            names.update(changed_names(item.then_body))
                            names.update(changed_names(item.else_body))
                        elif isinstance(item, LoopStatement):
                            names.update(changed_names(item.body))
                        elif isinstance(item, WhileStatement):
                            names.update(changed_names(item.body))
                        elif isinstance(item, ForStatement):
                            # A nested counter loop initializes and updates its counter.
                            names.add(item.counter_name)
                            names.update(changed_names(item.body))
                        else:
                            raise QIRASTLoweringError("While body supports assignments and if statements only")
                    return names

                # Branch-local transfers are handled by the existing If lowering:
                # terminated branches do not contribute an edge to the join.
                # Their snapshots are recorded as loop break/continue edges.
                modified = changed_names(statement.body)
                if any(name not in values for name in modified):
                    raise QIRASTLoweringError("While assigns an undeclared variable")
                before = dict(values)
                preheader = current_label
                header = next_label("while_header")
                body_label = next_label("while_body")
                exit_label = next_label("while_exit")
                close_block(QJump(header))
                current_label = header
                loop_phis = {name: fresh(before[name].type) for name in sorted(modified)}
                values.update(loop_phis)
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
                    back_edges.append((current_label, dict(values)))
                    close_block(QJump(header))
                header_block = blocks[header_index]
                phis = tuple(QPhi(loop_phis[name], tuple(
                    [(preheader, before[name])] +
                    [(label, snapshot[name]) for label, snapshot in back_edges]))
                    for name in sorted(modified))
                blocks[header_index] = QBlock(header_block.label, header_block.instructions,
                                              header_block.terminator, phis + header_block.phis)
                current_label = exit_label
                values.clear()
                values.update(before)
                values.update(loop_phis)
                break_edges = context["break_edges"]
                if break_edges:
                    # Merge normal condition-false exit with each early break.
                    for name in sorted(modified):
                        sources = [(header, loop_phis[name])] + [
                            (label, snapshot[name]) for label, snapshot in break_edges]
                        if len(set(value for _, value in sources)) > 1:
                            merged = fresh(before[name].type)
                            pending_phis.append(QPhi(merged, tuple(sources)))
                            values[name] = merged
            elif isinstance(statement, MatchStatement):
                if enum_layout is None:
                    raise QIRASTLoweringError("MatchStatement requires an enum layout")
                if not isinstance(statement.expression, Variable) or statement.expression.name not in values or values[statement.expression.name].type != QType("i32"):
                    raise QIRASTLoweringError("MatchStatement requires an i32 tag parameter or variable")
                if not statement.default_body:
                    raise QIRASTLoweringError("MatchStatement requires an explicit default for invalid tags")
                try:
                    plans = plan_match_bindings(enum_layout, statement.arms)
                    cases = [SwitchCase(Integer(plan.tag), rewrite_match_arm(arm.body, plan, declared_types, legacy=False))
                             for arm, plan in zip(statement.arms, plans)]
                except QIREnumLayoutError as exc:
                    raise QIRASTLoweringError(str(exc)) from exc
                return lower_statements([SwitchStatement(statement.expression, cases, statement.default_body)] + list(statements[index + 1:]), top_level=top_level)
            elif isinstance(statement, SwitchStatement):
                # Restrict the initial subset to a stable scrutinee, evaluated without side effects.
                if not isinstance(statement.expression, (Variable, Integer)):
                    raise QIRASTLoweringError("SwitchStatement requires a variable or integer scrutinee")
                if not statement.cases:
                    return lower_statements(list(statement.default_body) + list(statements[index + 1:]),
                                            top_level=top_level)
                tail = list(statement.default_body)
                for case in reversed(statement.cases):
                    if not isinstance(case.value, Integer):
                        raise QIRASTLoweringError("SwitchStatement supports integer literal cases only")
                    tail = [IfStatement(BinaryOperation(statement.expression, "==", case.value),
                                        list(case.body), tail)]
                return lower_statements(tail + list(statements[index + 1:]), top_level=top_level)
            elif isinstance(statement, IfStatement):
                condition = expression(statement.condition, QType("bool"))
                then_label = next_label("if_then")
                else_label = next_label("if_else")
                join_label = next_label("if_join")
                close_block(QBranch(condition, then_label, else_label))
                incoming = dict(values)

                current_label = then_label
                values.clear()
                values.update(incoming)
                then_return = lower_statements(statement.then_body)
                then_exit = current_label
                then_values = dict(values)
                if not then_return:
                    close_block(QJump(join_label))

                current_label = else_label
                values.clear()
                values.update(incoming)
                else_return = lower_statements(statement.else_body)
                else_exit = current_label
                else_values = dict(values)
                if not else_return:
                    close_block(QJump(join_label))

                if then_return and else_return:
                    return True
                current_label = join_label
                values.clear()
                if then_return or else_return:
                    values.update(else_values if then_return else then_values)
                else:
                    for name, original in incoming.items():
                        left, right = then_values[name], else_values[name]
                        if left == right:
                            values[name] = left
                        else:
                            merged = fresh(original.type)
                            pending_phis.append(QPhi(merged, ((then_exit, left), (else_exit, right))))
                            values[name] = merged
            elif isinstance(statement, ReturnStatement):
                if statement.value is None:
                    raise QIRASTLoweringError("A value-return is required")
                # A return terminates the current path. Any subsequent statements
                # in this sequence are unreachable and must not be lowered.
                close_block(QReturn(expression(statement.value, result_type)))
                return True
            else:
                raise QIRASTLoweringError(f"Unsupported AST statement: {type(statement).__name__}")
        return False

    terminated = lower_statements(function.body, top_level=True)
    if not terminated:
        raise QIRASTLoweringError("A final return statement is required")
    result = QFunction(function.name, result_type, tuple(params), tuple(blocks))
    try:
        validate_function(result)
    except ValueError as exc:
        raise QIRASTLoweringError(f"Generated QIR failed validation: {exc}") from exc
    return result
