"""Opt-in lowering of a scoped i32 Visual Quar subset to validated QIR.

Direct calls, lexical if/else blocks and SSA merges are supported. Loops,
captures, non-i32 data and early returns still fail closed.
"""
from __future__ import annotations

from ..ast_nodes import (ArrayDeclaration, ArrayAccess, ArrayAssignment, StructDefinition, ObjectDeclaration, MemberAccess, MemberAssignment, Assignment, BinaryOperation, Boolean, UnaryOperation, ConstantDeclaration,
                         FunctionCall, FunctionDefinition, ExternalFunctionDeclaration, ForStatement, IfStatement, Integer, BreakStatement, ContinueStatement,
                         ReturnStatement, String, Variable, VariableDeclaration, WhileStatement)
from .model import (QBlock, QBranch, QFunction, QInstruction, QJump,
                    QModule, QPhi, QReturn, QType, QValue, QMetadata, QSafetyMetadata)
from .validation import validate_module


class QIRProgramLoweringError(ValueError):
    """The validated AST exceeds the supported QIR program subset."""


_I32 = QType("i32")


def _i32_type(name: str | None) -> bool:
    """Accept only the i32 source type and its existing canonical alias."""
    return name in ("i32", "int")


class _ScopedFunction:
    """Build SSA values and lexical blocks for one independent function."""

    def __init__(self, name: str, parameters: tuple[QValue, ...],
                 signatures: dict[str, tuple[int, QType]],
                 *, native_symbols: frozenset[str] = frozenset(), native_parameter_types: dict[str, tuple[str, ...]] | None = None, allow_inferred_declarations: bool = False, struct_types: dict[str, tuple[str, ...]] | None = None):
        self.name = name
        self.parameters = parameters
        self.signatures = signatures
        self.native_symbols = native_symbols
        self.native_parameter_types = native_parameter_types or {}
        self.allow_inferred_declarations = allow_inferred_declarations
        self.values: dict[str, QValue] = {p.name: p for p in parameters}
        self.constants: set[str] = set()
        self.arrays: dict[str, QValue] = {}
        self.struct_types = struct_types if struct_types is not None else {}
        self.objects: dict[str, tuple[str, ...]] = {}
        self.blocks: list[QBlock] = []
        self.label = "entry"
        self.instructions: list[QInstruction] = []
        self.phis: list[QPhi] = []
        self.serial = 0
        self.block_serial = 0
        self.terminated = False
        self.return_type: QType | None = None
        self.loop_stack: list[dict] = []

    def fresh(self, value_type: QType = _I32) -> QValue:
        """Return a function-unique SSA value with an explicit QIR type."""
        self.serial += 1
        return QValue(f"$qir_{self.name}_{self.serial}", value_type)

    def emit(self, opcode: str, operands: tuple[QValue, ...] = (),
             immediate: int | str | None = None, *, value_type: QType = _I32) -> QValue:
        """Append an operation and return its typed SSA result."""
        result = self.fresh(value_type)
        self.instructions.append(QInstruction(opcode, operands, result, immediate))
        return result

    def new_label(self, suffix: str) -> str:
        """Return a unique control-flow label in this function."""
        self.block_serial += 1
        return f"{suffix}_{self.block_serial}"

    def close(self, terminator: QReturn | QJump | QBranch) -> None:
        """Finish the current block, preserving its instructions and phis."""
        self.blocks.append(QBlock(self.label, tuple(self.instructions), terminator,
                                  tuple(self.phis)))
        self.instructions = []
        self.phis = []
        self.terminated = True

    def open(self, label: str) -> None:
        """Start a new block; the previous block must already be closed."""
        self.label = label
        self.terminated = False

    def expression(self, node: object, *, expected_type: str | None = None) -> QValue:
        """Lower an i32 expression or i32 comparison into SSA operations."""
        if isinstance(node, String) and type(node.value) is str:
            if expected_type != "cstring":
                raise QIRProgramLoweringError("String literals require a native cstring parameter")
            if "\x00" in node.value:
                raise QIRProgramLoweringError("Native cstring cannot contain embedded NUL")
            return self.emit("string_const", immediate=node.value, value_type=QType("string"))
        if isinstance(node, Boolean) and type(node.value) is bool:
            return self.emit("const", immediate=node.value, value_type=QType("bool"))
        if isinstance(node, UnaryOperation) and node.operator.lower() in ("not", "!"):
            operand = self.expression(node.operand)
            if operand.type != QType("bool"):
                raise QIRProgramLoweringError("Logical NOT requires bool")
            return self.emit("logical_not", (operand,), value_type=QType("bool"))
        if isinstance(node, Integer) and type(node.value) is int:
            if expected_type in ("u32", "u64"):
                maximum = (1 << (32 if expected_type == "u32" else 64)) - 1
                if not 0 <= node.value <= maximum:
                    raise QIRProgramLoweringError(f"{expected_type} literal is out of range")
                return self.emit("const", immediate=node.value, value_type=QType(expected_type))
            if not -(1 << 31) <= node.value < (1 << 31):
                raise QIRProgramLoweringError("i32 literal is out of range")
            return self.emit("const", immediate=node.value)
        if isinstance(node, ArrayAccess):
            if node.name not in self.arrays or node.second_index is not None:
                raise QIRProgramLoweringError("Unknown or multidimensional array")
            index = self.expression(node.index)
            if index.type != _I32:
                raise QIRProgramLoweringError("Array index must be i32")
            result = self.fresh()
            self.instructions.append(QInstruction("array_get", (self.arrays[node.name], index), result,
                metadata=QMetadata(safety=QSafetyMetadata(checks=("bounds",)))))
            return result
        if isinstance(node, MemberAccess):
            fields = self.objects.get(node.object_name)
            if fields is None or node.member_name not in fields:
                raise QIRProgramLoweringError("Unknown structure field")
            return self.values[f"{node.object_name}.{node.member_name}"]
        if isinstance(node, Variable):
            if node.name not in self.values:
                raise QIRProgramLoweringError(f"Undefined variable: {node.name}")
            return self.values[node.name]
        if isinstance(node, BinaryOperation):
            if node.operator.lower() in ("and", "or", "&&", "||"):
                left = self.expression(node.left)
                if left.type != QType("bool"):
                    raise QIRProgramLoweringError("Logical left operand must be bool")
                is_and = node.operator.lower() in ("and", "&&")
                left_label = self.label
                rhs_label = self.new_label("logical_rhs")
                merge_label = self.new_label("logical_merge")
                self.close(QBranch(left, rhs_label if is_and else merge_label,
                                   merge_label if is_and else rhs_label))
                self.open(rhs_label)
                right = self.expression(node.right)
                if right.type != QType("bool"):
                    raise QIRProgramLoweringError("Logical right operand must be bool")
                right_label = self.label
                self.close(QJump(merge_label))
                self.open(merge_label)
                merged = self.fresh(QType("bool"))
                self.phis.append(QPhi(merged, ((left_label, left), (right_label, right))))
                return merged
            arithmetic = {"+": "add", "-": "sub", "*": "mul", "/": "div", "%": "mod"}
            comparisons = {"==": "eq", "!=": "ne", "<": "lt", "<=": "le",
                           ">": "gt", ">=": "ge"}
            if node.operator in arithmetic:
                operands = (self.expression(node.left), self.expression(node.right))
                if any(value.type != _I32 for value in operands):
                    raise QIRProgramLoweringError("Arithmetic requires i32 operands")
                return self.emit(arithmetic[node.operator], operands)
            if node.operator in comparisons:
                operands = (self.expression(node.left), self.expression(node.right))
                if any(value.type != _I32 for value in operands):
                    raise QIRProgramLoweringError("Comparison requires i32 operands")
                return self.emit(comparisons[node.operator], operands,
                                 value_type=QType("bool"))
        if isinstance(node, FunctionCall) and node.name != "print":
            signature = self.signatures.get(node.name)
            if signature is None or signature[1].name == "void":
                raise QIRProgramLoweringError(f"Unsupported function call: {node.name}")
            if len(node.arguments) != signature[0]:
                raise QIRProgramLoweringError(f"Function argument count mismatch: {node.name}")
            expected = self.native_parameter_types.get(node.name)
            operands = tuple(self.expression(argument, expected_type=expected[index] if expected else None)
                             for index, argument in enumerate(node.arguments))
            if any(value.type.name not in (("i32", "u32", "u64", "bool", "string", "opaque") if node.name in self.native_symbols else ("i32",)) for value in operands):
                raise QIRProgramLoweringError("Unsupported function argument type")
            self._validate_native_arguments(node.name, operands)
            return self.emit("native_call" if node.name in self.native_symbols else "call", operands, node.name, value_type=signature[1])
        raise QIRProgramLoweringError(f"Unsupported expression: {type(node).__name__}")

    def _validate_native_arguments(self, name: str, operands: tuple[QValue, ...]) -> None:
        """Reject native calls whose QIR argument types differ from their C ABI signature."""
        expected = self.native_parameter_types.get(name)
        if expected is None:
            return
        actual = tuple("cstring" if value.type.name == "string" else value.type.name for value in operands)
        if actual != expected:
            raise QIRProgramLoweringError(
                f"Native ABI argument type mismatch for {name}: expected {expected}, got {actual}"
            )

    def _branch_body(self, label: str, statements: list, original: dict[str, QValue],
                     original_constants: set[str], join: str) -> tuple[str | None, dict[str, QValue]]:
        """Lower a branch; a returned branch has no outgoing join edge."""
        self.open(label)
        self.values = dict(original)
        self.constants = set(original_constants)
        for statement in statements:
            if self.terminated:
                raise QIRProgramLoweringError("Unreachable statement after return")
            self.statement(statement)
        outgoing_values = dict(self.values)
        if self.terminated:
            return None, outgoing_values
        outgoing_label = self.label
        self.close(QJump(join))
        return outgoing_label, outgoing_values

    def _if_statement(self, node: IfStatement) -> None:
        """Lower lexical branches, allowing one or both branches to return."""
        condition = self.expression(node.condition)
        if condition.type.name != "bool":
            raise QIRProgramLoweringError("If condition must be bool")
        original = dict(self.values)
        original_constants = set(self.constants)
        then_label = self.new_label("then")
        else_label = self.new_label("else")
        join_label = self.new_label("join")
        self.close(QBranch(condition, then_label, else_label))
        then_pred, then_values = self._branch_body(
            then_label, node.then_body, original, original_constants, join_label)
        else_pred, else_values = self._branch_body(
            else_label, node.else_body, original, original_constants, join_label)
        if then_pred is None and else_pred is None:
            self.terminated = True
            return
        self.open(join_label)
        self.values = dict(original)
        self.constants = original_constants
        if then_pred is None:
            self.values.update({name: else_values[name] for name in original})
        elif else_pred is None:
            self.values.update({name: then_values[name] for name in original})
        else:
            for name in original:
                left, right = then_values[name], else_values[name]
                if left != right:
                    merged = self.fresh(left.type)
                    self.phis.append(QPhi(merged, ((then_pred, left), (else_pred, right))))
                    self.values[name] = merged

    def _while_statement(self, node: WhileStatement, postlude: object | None = None) -> None:
        """Lower a while loop with SSA merges for normal, break and continue edges."""
        before = dict(self.values)
        constants = set(self.constants)
        incoming_label = self.label
        header = self.new_label("while_header")
        body = self.new_label("while_body")
        exit_label = self.new_label("while_exit")
        self.close(QJump(header))
        self.open(header)
        header_phis = {name: self.fresh(value.type) for name, value in before.items()}
        self.values = dict(header_phis)
        condition = self.expression(node.condition)
        if condition.type.name != "bool":
            raise QIRProgramLoweringError("While condition must be bool")
        # Short-circuit conditions can change the actual header predecessor.
        condition_label = self.label
        header_index = len(self.blocks)
        self.close(QBranch(condition, body, exit_label))
        context = {"header": header, "exit": exit_label, "continues": [], "breaks": []}
        self.loop_stack.append(context)
        self.open(body)
        self.constants = set(constants)
        for statement in node.body:
            if self.terminated:
                raise QIRProgramLoweringError("Unreachable statement in while body")
            self.statement(statement)
        if not self.terminated and postlude is not None:
            self.statement(postlude)
        if not self.terminated:
            context["continues"].append((self.label, dict(self.values)))
            self.close(QJump(header))
        self.loop_stack.pop()
        back_edges = context["continues"]
        phis = tuple(QPhi(header_phis[name],
                          ((incoming_label, before[name]),) +
                          tuple((label, values[name]) for label, values in back_edges))
                     for name in before)
        # Header may include condition instructions; update its phis in place.
        for index, block in enumerate(self.blocks):
            if block.label == header:
                self.blocks[index] = QBlock(block.label, block.instructions, block.terminator, phis)
                break
        self.open(exit_label)
        self.constants = constants
        exit_edges = [(condition_label, dict(header_phis)), *context["breaks"]]
        self.values = dict(header_phis)
        if len(exit_edges) > 1:
            for name, value in header_phis.items():
                incoming = tuple((label, values[name]) for label, values in exit_edges)
                if len({v for _, v in incoming}) > 1:
                    merged = self.fresh(value.type)
                    self.phis.append(QPhi(merged, incoming))
                    self.values[name] = merged

    def _for_statement(self, node: ForStatement) -> None:
        """Lower a canonical counter loop through the existing while CFG.

        The counter is initialized once, tested before each iteration, and
        updated after the body. Transfers remain unsupported in this pass.
        """
        comparison = node.comparison
        if (not isinstance(comparison, BinaryOperation)
                or not isinstance(comparison.left, Variable)
                or comparison.left.name != node.counter_name
                or comparison.operator not in ("<", "<=", ">", ">=")):
            raise QIRProgramLoweringError("For requires a canonical counter comparison")
        direction = 1 if comparison.operator in ("<", "<=") else -1
        if (type(node.step) is not int or node.step <= 0
                or node.direction not in (0, direction)):
            raise QIRProgramLoweringError("Invalid for step or direction")
        if node.counter_name in self.constants:
            raise QIRProgramLoweringError("For counter cannot be constant")
        if node.counter_name not in self.values and not self.allow_inferred_declarations:
            raise QIRProgramLoweringError("For counter must be declared")
        self.statement(Assignment(node.counter_name, node.start))
        update = Assignment(node.counter_name, BinaryOperation(
            Variable(node.counter_name), "+" if direction == 1 else "-", Integer(node.step)))

        def inject_continue_update(items: list) -> list:
            """Run the for counter update before a continue targeting this loop.

            Nested loops own their continue statements and are left untouched.
            Returns a transformed list of statements without modifying the AST.
            """
            rewritten = []
            for item in items:
                if isinstance(item, ContinueStatement):
                    rewritten.extend((update, item))
                elif isinstance(item, IfStatement):
                    rewritten.append(IfStatement(item.condition,
                        inject_continue_update(item.then_body),
                        inject_continue_update(item.else_body)))
                else:
                    rewritten.append(item)
            return rewritten

        self._while_statement(WhileStatement(
            comparison, inject_continue_update(node.body)), postlude=update)

    def statement(self, node: object) -> QValue | None:
        """Lower one statement, returning a value only for terminal returns."""
        if isinstance(node, ArrayDeclaration):
            if (node.name in self.values or node.name in self.arrays or
                not _i32_type(node.element_type) or node.dynamic or
                node.second_size is not None or type(node.size) is not int or
                not 0 < node.size <= 1_000_000):
                raise QIRProgramLoweringError("Unsupported array declaration")
            initial = node.initial_values or []
            if len(initial) > node.size:
                raise QIRProgramLoweringError("Too many array initializers")
            array = self.emit("array_alloc", immediate=node.size, value_type=QType("ptr<i32>"))
            self.arrays[node.name] = array
            for index, element in enumerate(initial):
                value = self.expression(element)
                if value.type != _I32:
                    raise QIRProgramLoweringError("Array element must be i32")
                offset = self.emit("const", immediate=index)
                self.instructions.append(QInstruction("array_set", (array, offset, value),
                    metadata=QMetadata(safety=QSafetyMetadata(checks=("bounds",)))))
            return None
        if isinstance(node, ArrayAssignment):
            if node.name not in self.arrays or node.second_index is not None:
                raise QIRProgramLoweringError("Unknown or multidimensional array")
            index = self.expression(node.index)
            value = self.expression(node.value)
            if index.type != _I32 or value.type != _I32:
                raise QIRProgramLoweringError("Array index and value must be i32")
            self.instructions.append(QInstruction("array_set", (self.arrays[node.name], index, value),
                metadata=QMetadata(safety=QSafetyMetadata(checks=("bounds",)))))
            return None
        if isinstance(node, ObjectDeclaration):
            fields = self.struct_types.get(node.type_name)
            if fields is None:
                raise QIRProgramLoweringError(f"Unsupported structure type: {node.type_name}")
            if node.name in self.objects or node.name in self.values or len(node.arguments) != len(fields):
                raise QIRProgramLoweringError("Duplicate object or incorrect field count")
            values = [self.expression(argument) for argument in node.arguments]
            if any(value.type != _I32 for value in values):
                raise QIRProgramLoweringError("Structure fields must be i32")
            self.objects[node.name] = fields
            for field, value in zip(fields, values):
                self.values[f"{node.name}.{field}"] = value
            return None
        if isinstance(node, MemberAssignment):
            fields = self.objects.get(node.object_name)
            if fields is None or node.member_name not in fields:
                raise QIRProgramLoweringError("Unknown structure field")
            value = self.expression(node.value)
            if value.type != _I32:
                raise QIRProgramLoweringError("Structure field assignment requires i32")
            self.values[f"{node.object_name}.{node.member_name}"] = value
            return None
        if isinstance(node, (VariableDeclaration, ConstantDeclaration)):
            if node.name in self.values:
                raise QIRProgramLoweringError(f"Duplicate declaration: {node.name}")
            if node.var_type not in ("i32", "int", "u32", "u64", "bool", "opaque", "cstring", None):
                raise QIRProgramLoweringError(f"Unsupported declaration type: {node.var_type}")
            if node.value is None:
                raise QIRProgramLoweringError("Uninitialized declarations are not supported")
            value = self.expression(node.value, expected_type=node.var_type)
            if value.type != (QType("bool") if node.var_type == "bool" else QType("u32") if node.var_type == "u32" else QType("u64") if node.var_type == "u64" else QType("opaque") if node.var_type == "opaque" else QType("string") if node.var_type == "cstring" else _I32):
                raise QIRProgramLoweringError("Declaration type mismatch")
            self.values[node.name] = value
            if isinstance(node, ConstantDeclaration):
                self.constants.add(node.name)
            return None
        if isinstance(node, Assignment):
            if node.name in self.constants:
                raise QIRProgramLoweringError("Assignment to constant variable")
            if node.name not in self.values and not self.allow_inferred_declarations:
                raise QIRProgramLoweringError(f"Assignment to undeclared variable: {node.name}")
            value = self.expression(node.value, expected_type=self.values[node.name].type.name if node.name in self.values else None)
            if node.name in self.values and value.type != self.values[node.name].type:
                raise QIRProgramLoweringError("Assignment type mismatch")
            if node.name not in self.values and value.type != _I32:
                raise QIRProgramLoweringError("Inferred assignment requires i32")
            self.values[node.name] = value
            return None
        if isinstance(node, FunctionCall) and node.name != "print":
            signature = self.signatures.get(node.name)
            if signature is None or signature[1].name != "void":
                raise QIRProgramLoweringError(f"Unsupported statement call: {node.name}")
            if len(node.arguments) != signature[0]:
                raise QIRProgramLoweringError(f"Function argument count mismatch: {node.name}")
            expected = self.native_parameter_types.get(node.name)
            operands = tuple(self.expression(argument, expected_type=expected[index] if expected else None)
                             for index, argument in enumerate(node.arguments))
            if any(value.type.name not in (("i32", "u32", "u64", "bool", "string", "opaque") if node.name in self.native_symbols else ("i32",)) for value in operands):
                raise QIRProgramLoweringError("Unsupported function argument type")
            self._validate_native_arguments(node.name, operands)
            self.instructions.append(QInstruction("native_call_void" if node.name in self.native_symbols else "call_void", operands, None, node.name))
            return None
        if isinstance(node, FunctionCall) and node.name == "print" and len(node.arguments) == 1:
            value = self.expression(node.arguments[0])
            if value.type.name not in ("i32", "bool"):
                raise QIRProgramLoweringError("Only i32 and bool print are supported")
            self.instructions.append(QInstruction("print", (value,)))
            return None
        if isinstance(node, (BreakStatement, ContinueStatement)):
            if not self.loop_stack:
                raise QIRProgramLoweringError("Loop transfer outside loop")
            context = self.loop_stack[-1]
            is_break = isinstance(node, BreakStatement)
            context["breaks" if is_break else "continues"].append(
                (self.label, dict(self.values)))
            self.close(QJump(context["exit" if is_break else "header"]))
            return None
        if isinstance(node, ForStatement):
            self._for_statement(node)
            return None
        if isinstance(node, WhileStatement):
            self._while_statement(node)
            return None
        if isinstance(node, IfStatement):
            self._if_statement(node)
            return None
        if isinstance(node, ReturnStatement):
            if self.return_type is None:
                raise QIRProgramLoweringError("Return outside function")
            if node.value is None:
                if self.return_type.name != "void":
                    raise QIRProgramLoweringError("Missing return value")
                self.close(QReturn())
                return None
            result = self.expression(node.value)
            if result.type != self.return_type:
                raise QIRProgramLoweringError("Return type mismatch")
            self.close(QReturn(result))
            return result
        raise QIRProgramLoweringError(f"Unsupported statement: {type(node).__name__}")


def lower_ast_program(program: list, *, allow_inferred_declarations: bool = False) -> QModule:
    """Lower a semantically validated linear program to a QIR module.

    Returns an entry function and zero or more independent i32 functions.
    Unsupported features fail closed rather than using the legacy compiler.
    """
    struct_types: dict[str, tuple[str, ...]] = {}
    for statement in program:
        if isinstance(statement, StructDefinition):
            names = tuple(field.name for field in statement.fields)
            if (statement.name in struct_types or not names or
                    len(set(names)) != len(names) or
                    any(not _i32_type(field.field_type) for field in statement.fields)):
                raise QIRProgramLoweringError("Unsupported or duplicate i32 structure definition")
            struct_types[statement.name] = names
    definitions: dict[str, FunctionDefinition] = {}
    for statement in program:
        if isinstance(statement, FunctionDefinition):
            if statement.name in definitions or statement.name == "__qir_entry":
                raise QIRProgramLoweringError(f"Duplicate or reserved function: {statement.name}")
            if statement.return_type not in ("i32", "int", "bool", "void") or any(
                not _i32_type(p.var_type) or p.default_value is not None or
                p.is_variadic or p.callback_signature is not None
                for p in statement.parameters
            ):
                raise QIRProgramLoweringError(f"Unsupported function signature: {statement.name}")
            if len({p.name for p in statement.parameters}) != len(statement.parameters):
                raise QIRProgramLoweringError(f"Duplicate parameter: {statement.name}")
            definitions[statement.name] = statement

    native_declarations: dict[str, tuple[tuple[str, ...], str]] = {}
    for statement in program:
        if isinstance(statement, ExternalFunctionDeclaration):
            if (statement.abi != "C" or statement.output_struct is not None
                    or statement.return_type not in ("i32", "u32", "u64", "bool", "opaque", "cstring", "void")
                    or any(parameter.var_type not in ("i32", "u32", "u64", "bool", "opaque", "cstring") for parameter in statement.parameters)
                    or statement.name in definitions or statement.name in native_declarations
                    or statement.name == "__qir_entry"):
                raise QIRProgramLoweringError("Unsupported or conflicting native declaration")
            native_declarations[statement.name] = (
                tuple(parameter.var_type for parameter in statement.parameters), statement.return_type)

    signatures = {name: (len(definition.parameters), QType("bool") if definition.return_type == "bool" else QType("void") if definition.return_type == "void" else _I32)
                  for name, definition in definitions.items()}
    signatures.update({name: (len(arguments), QType("string" if result == "cstring" else result))
                       for name, (arguments, result) in native_declarations.items()})
    native_symbols = frozenset(native_declarations)
    functions: list[QFunction] = []
    for definition in definitions.values():
        params = tuple(QValue(parameter.name, _I32) for parameter in definition.parameters)
        builder = _ScopedFunction(definition.name, params, signatures, native_symbols=native_symbols, native_parameter_types={name: args for name, (args, _) in native_declarations.items()},
                                  allow_inferred_declarations=allow_inferred_declarations, struct_types=struct_types)
        builder.return_type = signatures[definition.name][1]
        for statement in definition.body:
            if builder.terminated:
                raise QIRProgramLoweringError("Unreachable statement after return")
            builder.statement(statement)
        if not builder.terminated:
            if builder.return_type.name == "void":
                builder.close(QReturn())
            else:
                raise QIRProgramLoweringError(f"Missing return: {definition.name}")
        functions.append(QFunction(definition.name, signatures[definition.name][1], params, tuple(builder.blocks)))

    entry = _ScopedFunction("entry", (), signatures, native_symbols=native_symbols, native_parameter_types={name: args for name, (args, _) in native_declarations.items()},
                            allow_inferred_declarations=allow_inferred_declarations, struct_types=struct_types)
    for statement in program:
        if not isinstance(statement, (FunctionDefinition, StructDefinition, ExternalFunctionDeclaration)):
            if isinstance(statement, ReturnStatement):
                raise QIRProgramLoweringError("Top-level return is not supported")
            entry.statement(statement)
    if not entry.instructions and not entry.blocks:
        raise QIRProgramLoweringError("Empty QIR entry program is not supported")
    entry.close(QReturn())
    entry_function = QFunction("__qir_entry", QType("void"), (), tuple(entry.blocks))
    module = QModule("qir_program", (entry_function, *functions),
                     tuple((name, arguments, result) for name, (arguments, result) in native_declarations.items()))
    validate_module(module)
    return module
