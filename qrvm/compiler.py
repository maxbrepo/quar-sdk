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


class QRVMCompiler:

    def __init__(self):
        self.functions = {}
        self.switch_counter = 0

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

    def compile(self, program):
        instructions = []
        self.type_fields = {}
        self.enum_types = set()

        for statement in program:
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
            "functions": {
                name: self.compile_function(function)
                for name, function in self.functions.items()
            },
        }
        # Return QRVM program package

    def compile_function(self, function):
        instructions = []

        for statement in function.body:
            self.extend_chunk(
                instructions,
                self.compile_statement(statement),
            )

        if function.return_type == "void":
            if not instructions or instructions[-1][0] != OpCode.RETURN:
                instructions.append((OpCode.RETURN, None))

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

        if isinstance(
            statement,
            (StructDefinition, RecordDefinition, EnumDefinition, TypeAlias),
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
            instructions.extend(
                self.compile_expression(statement.value)
            )
            instructions.append(
                (OpCode.STORE, statement.name)
            )
            return instructions
            # Store declared variable value

        if isinstance(statement, Assignment):
            instructions.extend(
                self.compile_expression(statement.value)
            )
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

    def compile_for_statement(self, statement):
        instructions = []

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
        return instructions
        # Compile automatic counter loop

    def compile_loop_statement(self, statement):
        instructions = []
        loop_start = 0

        for child in statement.body:
            self.extend_chunk(
                instructions,
                self.compile_statement(child),
            )

        instructions.append((OpCode.JUMP, loop_start))
        loop_end = len(instructions)
        return self.patch_loop_markers(
            instructions,
            loop_end,
            loop_start,
        )
        # Compile explicit infinite loop

    def compile_do_while_statement(self, statement):
        instructions = []
        loop_start = 0

        for child in statement.body:
            self.extend_chunk(
                instructions,
                self.compile_statement(child),
            )

        continue_target = len(instructions)
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
        return instructions
        # Compile post-test loop statement

    def compile_while_statement(self, statement):
        instructions = []
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
        return instructions
        # Compile while loop statement

    def compile_if_statement(self, statement):
        instructions = []
        instructions.extend(
            self.compile_expression(statement.condition)
        )

        jump_false_index = len(instructions)
        instructions.append(
            (OpCode.JUMP_IF_FALSE, None)
        )

        for child in statement.then_body:
            self.extend_chunk(
                instructions,
                self.compile_statement(child),
            )

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
        instructions=[]
        if isinstance(expression, TupleLiteral):
            for value in expression.values: instructions.extend(self.compile_expression(value))
            instructions.append((OpCode.TUPLE_NEW, len(expression.values)))
            return instructions
        if isinstance(expression, VariantConstructor):
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
            return instructions
            # Call user function

        raise RuntimeError(
            f"Unsupported QRVM expression: "
            f"{type(expression).__name__}"
        )
