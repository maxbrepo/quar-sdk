from frontend.quar.ast_nodes import (
    Integer,
    Double,
    Boolean,
    Variable,
    BinaryOperation,
    UnaryOperation,
    VariableDeclaration,
    ConstantDeclaration,
    Assignment,
    FunctionCall,
    WithFileStatement,
    TryCatchStatement, ThrowStatement,
    FunctionDefinition,
    ReturnStatement,
    IfStatement,
    WhileStatement,
    ForStatement,
    LoopStatement,
    ArrayDeclaration,
    ArrayAccess,
    ArrayAssignment,
    Char,
    String,
    ClassDefinition,
    StructDefinition,
    RecordDefinition,
    EnumDefinition,
    ObjectDeclaration,
    MemberAccess,
    MemberAssignment,
    DoWhileStatement,
    BreakStatement,
    ContinueStatement,
    SwitchStatement,
    TypeAlias,
    TupleLiteral, TupleDeclaration, DestructuringDeclaration,
    VariantConstructor, MatchStatement,
)

from .instructions import OpCode
from .optional_flow import FlowState, Presence


class QRVMCompiler:

    def __init__(self):
        self.functions = {}
        self.switch_counter = 0
        self._optional_variables = set()
        self._optional_presence = {}
        self._conditional_absence = set()
        self._declared_types = {}

    def extend_chunk(self, instructions, chunk):
        offset = len(instructions)
        for opcode, operand in chunk:
            if (
                opcode in (OpCode.JUMP, OpCode.JUMP_IF_FALSE)
                and isinstance(operand, int)
            ):
                operand += offset
            elif opcode == OpCode.MATCH_VARIANT and isinstance(operand, tuple) and isinstance(operand[2], int):
                operand = (operand[0], operand[1], operand[2] + offset)
            instructions.append((opcode, operand))
        # Relocate local jump targets

    def patch_loop_markers(
        self,
        instructions,
        break_target,
        continue_target,
    ):
        patched = []
        for opcode, operand in instructions:
            if opcode == OpCode.JUMP and operand == "__break__":
                patched.append((opcode, break_target))
            elif opcode == OpCode.JUMP and operand == "__continue__":
                patched.append((opcode, continue_target))
            else:
                patched.append((opcode, operand))
        return patched
        # Resolve loop control markers

    def compile(self, program, *, lexical=False, allow_inference=False):
        if lexical:
            from frontend.quar.lexical_bytecode import LexicalBytecodeLowerer
            program = LexicalBytecodeLowerer(
                allow_inference=allow_inference
            ).lower(program)
        self._optional_variables = set()
        self._optional_presence = {}
        self._conditional_absence = set()
        self._declared_types = {}
        instructions = []
        self.type_fields = {}
        self.enum_types = set()
        self.class_types = set()
        self.class_constructors = {}
        self.class_methods = {}
        self.class_objects = {}

        for statement in program:
            if isinstance(statement, ClassDefinition):
                self.type_fields[statement.name] = [field.name for field in statement.fields]
                self.class_types = getattr(self, "class_types", set())
                self.class_types.add(statement.name)
                if statement.constructor:
                    self.class_constructors[statement.name] = self.compile_function(
                        FunctionDefinition("void", "init", statement.constructor.parameters, statement.constructor.body)
                    )
                for method in statement.methods:
                    self.class_methods[(statement.name, method.function.name)] = self.compile_function(method.function)
            if isinstance(statement, (StructDefinition, RecordDefinition)):
                self.type_fields[statement.name] = [
                    field.name for field in statement.fields
                ]
            if isinstance(statement, EnumDefinition):
                self.enum_types.add(statement.name)

        for statement in program:
            if isinstance(statement, FunctionDefinition):
                self.functions[statement.name] = statement

        for statement in program:
            if isinstance(statement, FunctionDefinition):
                continue

            self.extend_chunk(
                instructions,
                self.compile_statement(statement),
            )

        instructions.append(
            (OpCode.HALT, None)
        )

        return {
            "instructions": instructions,
            "class_methods": self.class_methods,
            "functions": {
                name: self.compile_function(function)
                for name, function in self.functions.items()
            },
        }
        # Return QRVM program package

    def compile_function(self, function):
        instructions = []
        previous_optionals = self._optional_variables
        previous_presence = self._optional_presence
        previous_absence = self._conditional_absence
        previous_types = self._declared_types
        self._optional_variables = set()
        self._optional_presence = {}
        self._conditional_absence = set()
        self._declared_types = {p.name: p.var_type for p in function.parameters}

        for statement in function.body:
            self.extend_chunk(
                instructions,
                self.compile_statement(statement),
            )

        if function.return_type == "void":
            if not instructions or instructions[-1][0] != OpCode.RETURN:
                instructions.append((OpCode.RETURN, None))

        self._optional_variables = previous_optionals
        self._optional_presence = previous_presence
        self._conditional_absence = previous_absence
        self._declared_types = previous_types
        return {
            "parameters": [
                parameter.name
                for parameter in function.parameters
            ],
            "return_type": function.return_type,
            "instructions": instructions,
        }
        # Return compiled function body

    def compile_statement(self, statement):
        instructions = []
        if isinstance(statement, ThrowStatement):
            instructions.extend(self.compile_expression(statement.message))
            if statement.cause is not None:
                instructions.extend(self.compile_expression(statement.cause))
            instructions.append((OpCode.THROW, statement.cause is not None))
            return instructions
        if isinstance(statement, TryCatchStatement):
            try_body = []
            catch_body = []
            for inner in statement.try_body:
                self.extend_chunk(try_body, self.compile_statement(inner))
            for inner in statement.catch_body:
                self.extend_chunk(catch_body, self.compile_statement(inner))
            return [(OpCode.TRY_CATCH, (try_body, statement.error_name, catch_body))]

        if isinstance(statement, WithFileStatement):
            instructions.extend(self.compile_expression(statement.path))
            instructions.extend(self.compile_expression(statement.mode))
            previous = getattr(self, "_file_handles", set())
            self._file_handles = previous | {statement.name}
            try:
                body = []
                for inner in statement.body:
                    self.extend_chunk(body, self.compile_statement(inner))
            finally:
                self._file_handles = previous
            instructions.append((OpCode.WITH_FILE, (statement.name, body)))
            return instructions


        if isinstance(
            statement,
            (ClassDefinition, StructDefinition, RecordDefinition, EnumDefinition, TypeAlias),
        ):
            return instructions

        if isinstance(statement, TupleDeclaration):
            instructions.extend(self.compile_expression(statement.value))
            instructions.append((OpCode.STORE, statement.name))
            return instructions
        if isinstance(statement, DestructuringDeclaration):
            instructions.extend(self.compile_expression(statement.value))
            instructions.append((OpCode.TUPLE_UNPACK, [name for _, name in statement.bindings]))
            return instructions
        if isinstance(statement, MatchStatement):
            return self.compile_match_statement(statement)

        if isinstance(statement, BreakStatement):
            return [(OpCode.JUMP, "__break__")]

        if isinstance(statement, ContinueStatement):
            return [(OpCode.JUMP, "__continue__")]

        if isinstance(statement, SwitchStatement):
            return self.compile_switch_statement(statement)

        if isinstance(statement, ObjectDeclaration):
            if statement.type_name in self.class_types:
                self.class_objects[statement.name] = statement.type_name
                for argument in statement.arguments:
                    instructions.extend(self.compile_expression(argument))
                instructions.append((OpCode.OBJECT_NEW, (
                    statement.name, statement.type_name,
                    self.type_fields[statement.type_name], True,
                    self.class_constructors.get(statement.type_name),
                    len(statement.arguments),
                )))
                return instructions
            for argument in statement.arguments:
                instructions.extend(
                    self.compile_expression(argument)
                )
            instructions.append(
                (
                    OpCode.OBJECT_NEW,
                    (
                        statement.name,
                        statement.type_name,
                        self.type_fields[statement.type_name],
                    ),
                )
            )
            return instructions

        if isinstance(statement, MemberAssignment):
            instructions.extend(
                self.compile_expression(statement.value)
            )
            instructions.append(
                (
                    OpCode.MEMBER_STORE,
                    (
                        statement.object_name,
                        statement.member_name,
                    ),
                )
            )
            return instructions

        if isinstance(statement, ArrayDeclaration):
            default_values = {
                "int": 0,
                "short": 0,
                "ushort": 0,
                "uint": 0,
                "long": 0,
                "ulong": 0,
                "llong": 0,
                "ullong": 0,
                "double": 0.0,
                "long_double": 0.0,
                "bool": False,
                "char": "\\0",
                "string": "",
            }
            total_size = (
                len(statement.initial_values or [])
                if statement.dynamic
                else statement.size
            )
            if statement.second_size is not None:
                total_size *= statement.second_size

            initial_count = 0
            if statement.initial_values is not None:
                for value in statement.initial_values:
                    instructions.extend(
                        self.compile_expression(value)
                    )
                initial_count = len(statement.initial_values)

            instructions.append(
                (
                    OpCode.ARRAY_NEW,
                    (
                        statement.name,
                        total_size,
                        default_values.get(
                            statement.element_type,
                            None,
                        ),
                        initial_count,
                        statement.second_size,
                        statement.dynamic,
                    ),
                )
            )
            return instructions
            # Create fixed typed array

        if isinstance(statement, ArrayAssignment):
            instructions.extend(
                self.compile_expression(statement.index)
            )
            if statement.second_index is not None:
                instructions.extend(
                    self.compile_expression(statement.second_index)
                )
            instructions.extend(
                self.compile_expression(statement.value)
            )
            second_size = None
            instructions.append(
                (
                    OpCode.ARRAY_STORE,
                    (
                        statement.name,
                        statement.second_index is not None,
                    ),
                )
            )
            return instructions
            # Store array element value

        if isinstance(statement, (VariableDeclaration, ConstantDeclaration)):
            # Chapter 15.14: preserve optional values at the QRVM boundary.
            declared_type = statement.var_type
            if isinstance(declared_type, str):
                self._declared_types[statement.name] = declared_type
            if isinstance(declared_type, str) and declared_type.endswith("?"):
                self._optional_variables.add(statement.name)
                if statement.value is None:
                    instructions.append((OpCode.OPTIONAL_NONE, None))
                else:
                    instructions.extend(self.compile_expression(statement.value))
                    # Copy the tagged optional unchanged; never nest wrappers.
                    if not (isinstance(statement.value, Variable) and
                            statement.value.name in self._optional_variables):
                        instructions.append((OpCode.OPTIONAL_SOME, None))
            else:
                instructions.extend(self.compile_expression(statement.value))
            if statement.name in self._optional_variables:
                if statement.value is None:
                    self._optional_presence[statement.name] = False
                elif isinstance(statement.value, Variable) and statement.value.name in self._optional_variables:
                    self._optional_presence[statement.name] = self._optional_presence.get(statement.value.name)
                else:
                    self._optional_presence[statement.name] = True
            instructions.append((OpCode.STORE, statement.name))
            return instructions
            # Store declared variable value

        if isinstance(statement, Assignment):
            # Assignment invalidates any earlier branch-specific absence fact.
            self._conditional_absence.discard(statement.name)
            if statement.name in self._optional_variables and statement.value is None:
                instructions.append((OpCode.OPTIONAL_NONE, None))
            else:
                instructions.extend(self.compile_expression(statement.value))
                if (statement.name in self._optional_variables and
                        not (isinstance(statement.value, Variable) and
                             statement.value.name in self._optional_variables)):
                    instructions.append((OpCode.OPTIONAL_SOME, None))
            if statement.name in self._optional_variables:
                if statement.value is None:
                    self._optional_presence[statement.name] = False
                elif isinstance(statement.value, Variable) and statement.value.name in self._optional_variables:
                    self._optional_presence[statement.name] = self._optional_presence.get(statement.value.name)
                else:
                    self._optional_presence[statement.name] = True
            instructions.append(
                (OpCode.STORE, statement.name)
            )
            return instructions
            # Store assigned variable value

        if isinstance(statement, ForStatement):
            return self.compile_for_statement(statement)

        if isinstance(statement, LoopStatement):
            return self.compile_loop_statement(statement)

        if isinstance(statement, DoWhileStatement):
            return self.compile_do_while_statement(statement)

        if isinstance(statement, WhileStatement):
            return self.compile_while_statement(statement)

        if isinstance(statement, IfStatement):
            return self.compile_if_statement(statement)

        if isinstance(statement, ReturnStatement):
            if statement.value is not None:
                instructions.extend(
                    self.compile_expression(statement.value)
                )
            instructions.append(
                (OpCode.RETURN, statement.value is not None)
            )
            return instructions
            # Return function result value

        if isinstance(statement, FunctionCall):
            if statement.name == "panic":
                instructions.extend(self.compile_expression(statement.arguments[0]))
                instructions.append((OpCode.PANIC, None))
                return instructions
            if statement.name == "assert":
                instructions.extend(self.compile_expression(statement.arguments[0]))
                instructions.append((OpCode.ASSERT, None))
                return instructions
            if statement.name == "print":
                instructions.extend(
                    self.compile_expression(
                        statement.arguments[0]
                    )
                )
                instructions.append(
                    (OpCode.PRINT, None)
                )
                return instructions
                # Print expression result value

            if statement.name in {"stdout", "stderr", "exit"}:
                instructions.extend(self.compile_expression(statement.arguments[0]))
                opcode = OpCode.EXIT if statement.name == "exit" else OpCode.CONSOLE_WRITE
                instructions.append((opcode, statement.name))
                return instructions

            instructions.extend(
                self.compile_expression(statement)
            )
            if (
                statement.name in self.functions
                and self.functions[statement.name].return_type != "void"
            ):
                instructions.append(
                    (OpCode.POP, None)
                )
            return instructions
            # Discard unused non-void result

        raise RuntimeError(
            f"Unsupported QRVM statement: "
            f"{type(statement).__name__}"
        )

    def compile_switch_statement(self, statement):
        instructions = []
        end_jumps = []
        temp_name = f"__qr_switch_{self.switch_counter}"
        self.switch_counter += 1

        instructions.extend(
            self.compile_expression(statement.expression)
        )
        instructions.append((OpCode.STORE, temp_name))

        for case in statement.cases:
            instructions.append((OpCode.LOAD, temp_name))
            instructions.extend(
                self.compile_expression(case.value)
            )
            instructions.append((OpCode.EQUAL, None))

            next_case_index = len(instructions)
            instructions.append((OpCode.JUMP_IF_FALSE, None))

            for child in case.body:
                self.extend_chunk(
                    instructions,
                    self.compile_statement(child),
                )

            end_jumps.append(len(instructions))
            instructions.append((OpCode.JUMP, None))
            next_case = len(instructions)
            instructions[next_case_index] = (
                OpCode.JUMP_IF_FALSE,
                next_case,
            )

        for child in statement.default_body:
            self.extend_chunk(
                instructions,
                self.compile_statement(child),
            )

        switch_end = len(instructions)
        for index in end_jumps:
            instructions[index] = (OpCode.JUMP, switch_end)

        return instructions
        # Compile switch without fall-through

    def _invalidate_loop_facts(self):
        """Forget optional presence facts across a loop's back edge.

        A loop body may run zero, one, or many times. Until a fixed-point
        analysis exists, no pre-loop presence proof can be reused blindly.
        Declared types and optional-variable identity are retained.
        """
        self._invalidate_optional_call_facts()

    def compile_for_statement(self, statement):
        instructions = []
        self._invalidate_loop_facts()

        instructions.extend(
            self.compile_expression(statement.start)
        )
        instructions.append(
            (OpCode.STORE, statement.counter_name)
        )

        loop_start = len(instructions)

        instructions.extend(
            self.compile_expression(statement.comparison)
        )

        jump_end_index = len(instructions)
        instructions.append(
            (OpCode.JUMP_IF_FALSE, None)
        )

        for child in statement.body:
            self.extend_chunk(
                instructions,
                self.compile_statement(child),
            )

        continue_target = len(instructions)
        instructions.append(
            (OpCode.LOAD, statement.counter_name)
        )
        instructions.append(
            (OpCode.PUSH_INT, statement.step)
        )

        direction = statement.direction
        if direction == 0:
            direction = (
                1 if statement.comparison.operator in {"<", "<="} else -1
            )

        if direction > 0:
            instructions.append(
                (OpCode.ADD, None)
            )
        else:
            instructions.append(
                (OpCode.SUB, None)
            )

        instructions.append(
            (OpCode.STORE, statement.counter_name)
        )
        instructions.append(
            (OpCode.JUMP, loop_start)
        )

        loop_end = len(instructions)
        instructions[jump_end_index] = (
            OpCode.JUMP_IF_FALSE,
            loop_end,
        )

        instructions = self.patch_loop_markers(
            instructions,
            loop_end,
            continue_target,
        )
        self._invalidate_loop_facts()
        return instructions
        # Compile automatic counter loop

    def compile_loop_statement(self, statement):
        instructions = []
        self._invalidate_loop_facts()
        loop_start = 0

        for child in statement.body:
            self.extend_chunk(
                instructions,
                self.compile_statement(child),
            )

        instructions.append((OpCode.JUMP, loop_start))
        loop_end = len(instructions)
        self._invalidate_loop_facts()
        return self.patch_loop_markers(
            instructions,
            loop_end,
            loop_start,
        )
        # Compile explicit infinite loop

    def compile_do_while_statement(self, statement):
        instructions = []
        self._invalidate_loop_facts()
        loop_start = 0

        for child in statement.body:
            self.extend_chunk(
                instructions,
                self.compile_statement(child),
            )

        continue_target = len(instructions)
        self._require_boolean_condition(statement.condition)
        instructions.extend(
            self.compile_expression(statement.condition)
        )
        instructions.append(
            (OpCode.JUMP_IF_FALSE, len(instructions) + 2)
        )
        instructions.append(
            (OpCode.JUMP, loop_start)
        )
        loop_end = len(instructions)
        instructions = self.patch_loop_markers(
            instructions,
            loop_end,
            continue_target,
        )
        self._invalidate_loop_facts()
        return instructions
        # Compile post-test loop statement

    def compile_while_statement(self, statement):
        instructions = []
        self._invalidate_loop_facts()
        loop_start = 0

        instructions.extend(
            self.compile_expression(statement.condition)
        )

        jump_end_index = len(instructions)
        instructions.append(
            (OpCode.JUMP_IF_FALSE, None)
        )

        for child in statement.body:
            self.extend_chunk(
                instructions,
                self.compile_statement(child),
            )

        instructions.append(
            (OpCode.JUMP, loop_start)
        )

        loop_end = len(instructions)
        instructions[jump_end_index] = (
            OpCode.JUMP_IF_FALSE,
            loop_end,
        )

        instructions = self.patch_loop_markers(
            instructions,
            loop_end,
            loop_start,
        )
        self._invalidate_loop_facts()
        return instructions
        # Compile while loop statement

    def _known_expression_type(self, expression):
        """Return a provable primitive type, or None for unknown expressions."""
        if isinstance(expression, Boolean):
            return "bool"
        if isinstance(expression, Integer):
            return "int"
        if isinstance(expression, Double):
            return "double"
        if isinstance(expression, Variable):
            return self._declared_types.get(expression.name)
        if isinstance(expression, FunctionCall):
            if expression.name == "present":
                return "bool"
            function = self.functions.get(expression.name)
            return function.return_type if function is not None else None
        if isinstance(expression, UnaryOperation):
            if expression.operator == "not":
                return "bool"
            return self._known_expression_type(expression.operand)
        if isinstance(expression, BinaryOperation):
            if expression.operator in {"and", "or", "==", "!=", "<", "<=", ">", ">="}:
                return "bool"
        return None

    def _require_boolean_condition(self, expression):
        known = self._known_expression_type(expression)
        if known is not None and known != "bool":
            raise ValueError(f"logical condition requires bool, got {known}")

    def _invalidate_optional_call_facts(self):
        """Discard flow proofs across calls with unanalysed side effects.

        The runtime optional representation is unchanged; only compile-time
        knowledge is invalidated. Type declarations remain valid.
        """
        for name in self._optional_variables:
            self._optional_presence[name] = None
        self._conditional_absence.clear()

    def _condition_has_unknown_call(self, expression):
        """Detect a call whose effects cannot yet be proven harmless."""
        if isinstance(expression, FunctionCall):
            if expression.name not in {"present", "unwrap"}:
                return True
            return any(self._condition_has_unknown_call(arg) for arg in expression.arguments)
        if isinstance(expression, BinaryOperation):
            return (self._condition_has_unknown_call(expression.left) or
                    self._condition_has_unknown_call(expression.right))
        if isinstance(expression, UnaryOperation):
            return self._condition_has_unknown_call(expression.operand)
        return False

    def _condition_facts(self, condition, outcome):
        # Only facts guaranteed by the selected outcome are propagated.
        if (isinstance(condition, FunctionCall) and condition.name == "present"
                and len(condition.arguments) == 1
                and isinstance(condition.arguments[0], Variable)
                and condition.arguments[0].name in self._optional_variables):
            return {condition.arguments[0].name: outcome}
        if isinstance(condition, BinaryOperation):
            if (condition.operator == "and" and outcome) or (condition.operator == "or" and not outcome):
                left = self._condition_facts(condition.left, outcome)
                right = self._condition_facts(condition.right, outcome)
                return {**left, **right} if all(k not in left or left[k] == v for k, v in right.items()) else {}
        return {}

    def _apply_optional_facts(self, facts):
        for name, present in facts.items():
            self._optional_presence[name] = present
            if present:
                self._conditional_absence.discard(name)
            else:
                self._conditional_absence.add(name)

    def compile_if_statement(self, statement):
        # Branch facts are local. Only a direct present(optional_variable)
        # condition refines the two paths; no inference from arbitrary calls.
        incoming_presence = self._optional_presence.copy()
        incoming_absence = self._conditional_absence.copy()
        self._require_boolean_condition(statement.condition)
        unsafe_condition = self._condition_has_unknown_call(statement.condition)
        then_facts = {} if unsafe_condition else self._condition_facts(statement.condition, True)
        else_facts = {} if unsafe_condition else self._condition_facts(statement.condition, False)
        instructions = []
        instructions.extend(
            self.compile_expression(statement.condition)
        )

        jump_false_index = len(instructions)
        instructions.append(
            (OpCode.JUMP_IF_FALSE, None)
        )

        # The condition itself may call code that changes optional state.
        branch_base_presence = self._optional_presence.copy()
        branch_base_absence = self._conditional_absence.copy()
        self._apply_optional_facts(then_facts)
        for child in statement.then_body:
            self.extend_chunk(
                instructions,
                self.compile_statement(child),
            )

        then_presence = self._optional_presence.copy()
        then_absence = self._conditional_absence.copy()
        self._optional_presence = branch_base_presence.copy()
        self._conditional_absence = branch_base_absence.copy()
        self._apply_optional_facts(else_facts)
        if statement.else_body:
            jump_end_index = len(instructions)
            instructions.append(
                (OpCode.JUMP, None)
            )

            else_start = len(instructions)
            instructions[jump_false_index] = (
                OpCode.JUMP_IF_FALSE,
                else_start,
            )

            for child in statement.else_body:
                self.extend_chunk(
                    instructions,
                    self.compile_statement(child),
                )

            end_index = len(instructions)
            instructions[jump_end_index] = (
                OpCode.JUMP,
                end_index,
            )
        else:
            end_index = len(instructions)
            instructions[jump_false_index] = (
                OpCode.JUMP_IF_FALSE,
                end_index,
            )

        else_presence = self._optional_presence.copy()
        else_absence = self._conditional_absence.copy()
        # A fact survives the join only if it holds on both reachable paths.
        # Preserve definite absence across nested conditionals; do not leak
        # facts that were true in just one branch.
        def to_flow(presence):
            return FlowState.from_mapping({
                name: (Presence.PRESENT if presence.get(name) is True else
                       Presence.ABSENT if presence.get(name) is False else Presence.UNKNOWN)
                for name in self._optional_variables
            })

        merged = to_flow(then_presence).join(to_flow(else_presence))
        self._optional_presence = {
            name: (True if merged.get(name) is Presence.PRESENT else
                   False if merged.get(name) is Presence.ABSENT else None)
            for name in self._optional_variables
        }
        self._conditional_absence = {
            name for name in then_absence.intersection(else_absence)
            if merged.get(name) is Presence.ABSENT
        }
        return instructions
        # Compile conditional statement

    def compile_match_statement(self, statement):
        instructions=[]; end_jumps=[]; checks=[]; starts=[]
        for arm in statement.arms:
            starts.append(len(instructions))
            instructions.extend(self.compile_expression(statement.expression))
            check_index=len(instructions); checks.append(check_index)
            instructions.append((OpCode.MATCH_VARIANT, (arm.variant_name, arm.bindings, None)))
            for child in arm.body: self.extend_chunk(instructions, self.compile_statement(child))
            end_jumps.append(len(instructions)); instructions.append((OpCode.JUMP, None))
        default_start=len(instructions)
        for child in statement.default_body: self.extend_chunk(instructions, self.compile_statement(child))
        end=len(instructions)
        for i, check_index in enumerate(checks):
            target = starts[i + 1] if i + 1 < len(starts) else default_start
            arm = statement.arms[i]
            instructions[check_index]=(OpCode.MATCH_VARIANT,(arm.variant_name, arm.bindings,target))
        for index in end_jumps: instructions[index]=(OpCode.JUMP,end)
        return instructions

    def compile_expression(self, expression):
        # Chapter 15.16: internal AST bridge for optional runtime operations.
        # These names are not yet part of the public Visual Quar syntax.
        if isinstance(expression, FunctionCall) and expression.name in {"present", "unwrap"}:
            if len(expression.arguments) != 1:
                raise ValueError(f"{expression.name} expects exactly one argument")
            argument = expression.arguments[0]
            if not isinstance(argument, Variable) or argument.name not in self._optional_variables:
                raise ValueError(f"{expression.name} requires a known optional variable")
            if expression.name == "unwrap" and argument.name in self._conditional_absence:
                raise ValueError(f"unwrap of definitely absent optional: {argument.name}")
            result = self.compile_expression(argument)
            opcode = (OpCode.OPTIONAL_IS_PRESENT if expression.name == "present"
                      else OpCode.OPTIONAL_UNWRAP)
            result.append((opcode, None))
            return result
        if isinstance(expression, FunctionCall) and "." in expression.name:
            handle, method = expression.name.split(".", 1)
            if handle in getattr(self, "_file_handles", set()):
                instructions = []
                for argument in expression.arguments:
                    instructions.extend(self.compile_expression(argument))
                instructions.append((OpCode.HANDLE_OP, (handle, method, len(expression.arguments))))
                return instructions
        instructions=[]
        if isinstance(expression, TupleLiteral):
            for value in expression.values: instructions.extend(self.compile_expression(value))
            instructions.append((OpCode.TUPLE_NEW, len(expression.values)))
            return instructions
        if isinstance(expression, VariantConstructor) and expression.enum_name in getattr(self, "_file_handles", set()):
            instructions = []
            for argument in expression.arguments:
                instructions.extend(self.compile_expression(argument))
            instructions.append((OpCode.HANDLE_OP, (
                expression.enum_name, expression.variant_name, len(expression.arguments),
            )))
            return instructions
        if isinstance(expression, VariantConstructor) and expression.enum_name == "Console":
            instructions = []
            for argument in expression.arguments:
                instructions.extend(self.compile_expression(argument))
            instructions.append((OpCode.CONSOLE_QUERY, "Console." + expression.variant_name))
            return instructions
        if isinstance(expression, VariantConstructor) and expression.enum_name in {"File", "Directory", "Path", "Bytes"}:
            for value in expression.arguments:
                instructions.extend(self.compile_expression(value))
            instructions.append((OpCode.FILE_OP, (
                expression.enum_name + "." + expression.variant_name, len(expression.arguments),
            )))
            return instructions
        if isinstance(expression, VariantConstructor):
            qualified_name = expression.enum_name + "." + expression.variant_name
            if qualified_name in self.functions:
                for value in expression.arguments:
                    instructions.extend(self.compile_expression(value))
                instructions.append((OpCode.CALL, (qualified_name, len(expression.arguments))))
                return instructions
            if expression.enum_name in self.class_objects or expression.enum_name == "this":
                for value in expression.arguments:
                    instructions.extend(self.compile_expression(value))
                instructions.append((OpCode.CALL, (
                    expression.enum_name + "." + expression.variant_name,
                    len(expression.arguments),
                )))
                return instructions
            for value in expression.arguments: instructions.extend(self.compile_expression(value))
            instructions.append((OpCode.VARIANT_NEW,(expression.enum_name, expression.variant_name, len(expression.arguments))))
            return instructions
        instructions = []

        if isinstance(expression, Char):
            instructions.append(
                (OpCode.PUSH_CHAR, expression.value)
            )
            return instructions

        if isinstance(expression, String):
            instructions.append(
                (OpCode.PUSH_STRING, expression.value)
            )
            return instructions

        if isinstance(expression, MemberAccess):
            if expression.member_name == "length":
                instructions.append(
                    (OpCode.LENGTH, expression.object_name)
                )
                return instructions
            if expression.object_name in self.enum_types:
                instructions.append(
                    (
                        OpCode.PUSH_STRING,
                        f"{expression.object_name}.{expression.member_name}",
                    )
                )
                return instructions
            instructions.append(
                (
                    OpCode.MEMBER_LOAD,
                    (
                        expression.object_name,
                        expression.member_name,
                    ),
                )
            )
            return instructions

        if isinstance(expression, Integer):
            instructions.append(
                (OpCode.PUSH_INT, expression.value)
            )
            return instructions
            # Push integer onto stack

        if isinstance(expression, Double):
            instructions.append(
                (OpCode.PUSH_DOUBLE, expression.value)
            )
            return instructions
            # Push double onto stack

        if isinstance(expression, Boolean):
            instructions.append(
                (OpCode.PUSH_BOOL, expression.value)
            )
            return instructions
            # Push boolean onto stack

        if isinstance(expression, ArrayAccess):
            instructions.extend(
                self.compile_expression(expression.index)
            )
            if expression.second_index is not None:
                instructions.extend(
                    self.compile_expression(expression.second_index)
                )
            instructions.append(
                (
                    OpCode.ARRAY_LOAD,
                    (
                        expression.name,
                        expression.second_index is not None,
                    ),
                )
            )
            return instructions
            # Load indexed sequence value

        if isinstance(expression, Variable):
            instructions.append(
                (OpCode.LOAD, expression.name)
            )
            return instructions
            # Load variable onto stack

        if isinstance(expression, UnaryOperation):
            instructions.extend(
                self.compile_expression(expression.operand)
            )

            unary_operators = {
                "not": OpCode.LOGICAL_NOT,
                "-": OpCode.NEGATE,
                "~": OpCode.BIT_NOT,
            }

            if expression.operator not in unary_operators:
                raise RuntimeError(
                    f"Unsupported unary operator: "
                    f"{expression.operator}"
                )

            instructions.append(
                (unary_operators[expression.operator], None)
            )
            return instructions
            # Compile unary expression

        if isinstance(expression, BinaryOperation) and expression.operator in {"and", "or"}:
            self._require_boolean_condition(expression.left)
            self._require_boolean_condition(expression.right)
            # Short circuit: the right operand is compiled under the facts
            # established by the left operand's evaluated outcome.
            instructions.extend(self.compile_expression(expression.left))
            branch_index = len(instructions)
            instructions.append((OpCode.JUMP_IF_FALSE, None))
            if expression.operator == "and":
                right_start = len(instructions)
                saved_presence = self._optional_presence.copy()
                saved_absence = self._conditional_absence.copy()
                try:
                    self._apply_optional_facts(self._condition_facts(expression.left, True))
                    self.extend_chunk(instructions, self.compile_expression(expression.right))
                finally:
                    self._optional_presence = saved_presence
                    self._conditional_absence = saved_absence
                jump_end = len(instructions)
                instructions.append((OpCode.JUMP, None))
                false_start = len(instructions)
                instructions.append((OpCode.PUSH_BOOL, False))
                end = len(instructions)
                instructions[branch_index] = (OpCode.JUMP_IF_FALSE, false_start)
                instructions[jump_end] = (OpCode.JUMP, end)
            else:
                instructions.append((OpCode.PUSH_BOOL, True))
                jump_end = len(instructions)
                instructions.append((OpCode.JUMP, None))
                right_start = len(instructions)
                saved_presence = self._optional_presence.copy()
                saved_absence = self._conditional_absence.copy()
                try:
                    self._apply_optional_facts(self._condition_facts(expression.left, False))
                    self.extend_chunk(instructions, self.compile_expression(expression.right))
                finally:
                    self._optional_presence = saved_presence
                    self._conditional_absence = saved_absence
                end = len(instructions)
                instructions[branch_index] = (OpCode.JUMP_IF_FALSE, right_start)
                instructions[jump_end] = (OpCode.JUMP, end)
            return instructions

        if isinstance(expression, BinaryOperation):
            instructions.extend(
                self.compile_expression(expression.left)
            )
            instructions.extend(
                self.compile_expression(expression.right)
            )

            operators = {
                "+": OpCode.ADD,
                "-": OpCode.SUB,
                "*": OpCode.MUL,
                "/": OpCode.DIV,
                "%": OpCode.MOD,
                "&": OpCode.BIT_AND,
                "|": OpCode.BIT_OR,
                "^": OpCode.BIT_XOR,
                "<<": OpCode.SHIFT_LEFT,
                ">>": OpCode.SHIFT_RIGHT,
                "==": OpCode.EQUAL,
                "!=": OpCode.NOT_EQUAL,
                "<": OpCode.LESS,
                "<=": OpCode.LESS_EQUAL,
                ">": OpCode.GREATER,
                ">=": OpCode.GREATER_EQUAL,
                "and": OpCode.LOGICAL_AND,
                "or": OpCode.LOGICAL_OR,
            }

            if expression.operator not in operators:
                raise RuntimeError(
                    f"Unsupported operator "
                    f"'{expression.operator}'"
                )

            instructions.append(
                (
                    operators[expression.operator],
                    None,
                )
            )
            return instructions
            # Return binary operation instructions

        if isinstance(expression, FunctionCall):
            if expression.name in {"Console.arg_count", "Console.arg", "Console.env", "Console.env_exists"}:
                for argument in expression.arguments:
                    instructions.extend(self.compile_expression(argument))
                instructions.append((OpCode.CONSOLE_QUERY, expression.name))
                return instructions
            if expression.name == "input":
                if expression.arguments:
                    instructions.extend(self.compile_expression(expression.arguments[0]))
                instructions.append((OpCode.INPUT, bool(expression.arguments)))
                return instructions

            if expression.name in {
                "File.read_text", "File.write_text", "File.write_text_atomic", "File.append_text",
                "File.exists", "File.delete", "File.copy", "File.move",
                "Directory.create", "Directory.exists", "Directory.delete",
                "Path.join", "Path.name", "Path.parent",
                "File.size", "Directory.count", "Directory.create_all",
                "File.read_line", "File.read_range",
                "File.line_count",
                "File.read_bytes", "File.write_bytes", "File.write_bytes_atomic",
                "File.append_bytes", "File.read_bytes_range",
                "Bytes.from_hex", "Bytes.to_hex", "Bytes.length",
                "File.read_bytes_hex",
                "File.write_bytes_hex",
                "File.append_bytes_hex",
                "File.read_bytes_hex_range",
                "Directory.is_empty",
                "Directory.list_text",
                "Directory.entry",
                "Directory.entry_is_file",
                "Directory.entry_is_directory",
                "Path.suffix",
                "Path.stem",
                "Path.absolute",
                "Path.normalize",
            }:
                for argument in expression.arguments:
                    instructions.extend(self.compile_expression(argument))
                instructions.append((OpCode.FILE_OP, (expression.name, len(expression.arguments))))
                return instructions
            string_builtins = {
                "substring", "find", "replace", "trim",
                "to_string", "to_int", "to_double",
            }
            if expression.name in string_builtins:
                for argument in expression.arguments:
                    instructions.extend(self.compile_expression(argument))
                instructions.append(
                    (OpCode.STRING_OP, (expression.name, len(expression.arguments)))
                )
                return instructions

            if expression.name == "sum":
                instructions.extend(
                    self.compile_expression(
                        expression.arguments[0]
                    )
                )
                instructions.extend(
                    self.compile_expression(
                        expression.arguments[1]
                    )
                )
                instructions.append(
                    (OpCode.ADD, None)
                )
                return instructions
                # Return sum expression instructions

            if "." in expression.name:
                object_name, method_name = expression.name.split(".", 1)
                for argument in expression.arguments:
                    instructions.extend(self.compile_expression(argument))
                instructions.append((OpCode.CALL, (expression.name, len(expression.arguments))))
                self._invalidate_optional_call_facts()
                return instructions

            for argument in expression.arguments:
                instructions.extend(
                    self.compile_expression(argument)
                )

            instructions.append(
                (
                    OpCode.CALL,
                    (
                        expression.name,
                        len(expression.arguments),
                    ),
                )
            )
            self._invalidate_optional_call_facts()
            return instructions
            # Call user function

        raise RuntimeError(
            f"Unsupported QRVM expression: "
            f"{type(expression).__name__}"
        )
