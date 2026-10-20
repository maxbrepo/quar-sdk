from .errors import SemanticError
from .scope_symbols import LexicalBindings, DuplicateBindingError
from .numeric_types import (
    INTEGER_BITS,
    FLOAT_BITS,
    canonical_numeric_type,
    integer_range,
    is_integer_type,
    is_float_type,
    is_numeric_type,
    integer_conversion_is_safe,
)

from .ast_nodes import (
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
    NamedArgument,
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
    EnumVariant, VariantConstructor, MatchStatement,
)


class SemanticAnalyzer:

    def __init__(self, allow_lexical_shadowing=False):
        self.allow_lexical_shadowing = allow_lexical_shadowing
        self.variables = {}
        self.arrays = {}
        self.types = {}
        self.objects = {}
        self.functions = {
            "print": {
                "arguments": 1,
                "return_type": "void",
                "parameter_types": None,
            },
            "sum": {
                "arguments": 2,
                "return_type": "int",
                "parameter_types": ["int", "int"],
            },
        }
        self.current_return_type = None
        self.aliases = {}
        self.constants = set()
        self.loop_depth = 0
        self.tuple_types = {}
        self.lexical_bindings = LexicalBindings()

    def analyze(self, program):
        for statement in program:
            if isinstance(statement, FunctionDefinition):
                self.register_function(statement)

        for statement in program:
            self.analyze_statement(statement)

        return program

    def analyze_statement(self, statement):
        if isinstance(statement, ThrowStatement):
            if self.resolve_type(self.analyze_expression(statement.message)) != "string":
                raise SemanticError("throw requires a string message")
            if statement.cause is not None and self.resolve_type(self.analyze_expression(statement.cause)) != "quar_error":
                raise SemanticError("throw cause must be a caught error")
            return
        if isinstance(statement, TryCatchStatement):
            if statement.error_name in self.variables:
                raise SemanticError("catch variable already declared")
            for inner in statement.try_body:
                self.analyze_statement(inner)
            self.variables[statement.error_name] = "quar_error"
            try:
                for inner in statement.catch_body:
                    self.analyze_statement(inner)
            finally:
                del self.variables[statement.error_name]
            return

        if isinstance(statement, WithFileStatement):
            if self.analyze_expression(statement.path) != "string" or self.analyze_expression(statement.mode) != "string":
                raise SemanticError("File.open requires string path and mode")
            if statement.name in self.variables:
                raise SemanticError("File handle name already declared")
            if not isinstance(statement.mode, String):
                raise SemanticError("File.open mode must be a string literal for typed handles")
            binary = "b" in statement.mode.value
            self.variables[statement.name] = "file_handle_binary" if binary else "file_handle"
            try:
                for inner in statement.body:
                    self.analyze_statement(inner)
            finally:
                del self.variables[statement.name]
            return

        if isinstance(statement, TupleDeclaration):
            types = [self.analyze_expression(v) for v in statement.value.values]
            self.variables[statement.name] = "tuple"
            self.tuple_types[statement.name] = types
            return
        if isinstance(statement, DestructuringDeclaration):
            if not isinstance(statement.value, Variable) or statement.value.name not in self.tuple_types:
                raise SemanticError("Destructuring requires a known tuple")
            source_types = self.tuple_types[statement.value.name]
            if len(source_types) != len(statement.bindings):
                raise SemanticError("Destructuring arity mismatch")
            for (expected, name), actual in zip(statement.bindings, source_types):
                if not self.types_compatible(expected, actual):
                    raise SemanticError(f"Cannot destructure '{actual}' into '{expected}'")
                self.variables[name] = expected
            return
        if isinstance(statement, MatchStatement):
            self.analyze_match_statement(statement)
            return
        if isinstance(statement, TypeAlias):
            self.register_alias(statement)
            return
        if isinstance(statement, BreakStatement):
            if self.loop_depth == 0:
                raise SemanticError(
                    "Break statement outside loop"
                )
            return
        if isinstance(statement, ContinueStatement):
            if self.loop_depth == 0:
                raise SemanticError(
                    "Continue statement outside loop"
                )
            return
        if isinstance(statement, SwitchStatement):
            self.analyze_switch_statement(statement)
            return
        if isinstance(statement, ClassDefinition):
            if statement.name in self.types:
                raise SemanticError(f"Duplicate type '{statement.name}'")
            self.types[statement.name] = {"kind": "class", "fields": statement.fields, "immutable": False, "constructor": statement.constructor, "methods": {method.function.name: method.function for method in statement.methods}}
            if statement.constructor:
                saved_variables = self.variables.copy()
                saved_objects = self.objects.copy()
                self.variables["this"] = statement.name
                self.objects["this"] = statement.name
                for parameter in statement.constructor.parameters:
                    self.variables[parameter.name] = parameter.var_type
                for child in statement.constructor.body:
                    self.analyze_statement(child)
                self.variables = saved_variables
                self.objects = saved_objects
            for method in statement.methods:
                saved_variables = self.variables.copy()
                saved_objects = self.objects.copy()
                saved_return_type = self.current_return_type
                self.variables["this"] = statement.name
                self.objects["this"] = statement.name
                self.current_return_type = method.function.return_type
                for parameter in method.function.parameters:
                    self.variables[parameter.name] = parameter.var_type
                for child in method.function.body:
                    self.analyze_statement(child)
                self.current_return_type = saved_return_type
                self.variables = saved_variables
                self.objects = saved_objects
            return
        if isinstance(statement, StructDefinition):
            self.register_composite(statement, False)
            return
        if isinstance(statement, RecordDefinition):
            self.register_composite(statement, True)
            return
        if isinstance(statement, EnumDefinition):
            self.register_enum(statement)
            return
        if isinstance(statement, ObjectDeclaration):
            self.analyze_object_declaration(statement)
            return
        if isinstance(statement, MemberAssignment):
            self.analyze_member_assignment(statement)
            return
        if isinstance(statement, FunctionDefinition):
            self.analyze_function_definition(statement)
            return
        if isinstance(statement, ForStatement):
            self.analyze_for_statement(statement)
            return
        if isinstance(statement, LoopStatement):
            self.analyze_loop_statement(statement)
            return
        if isinstance(statement, DoWhileStatement):
            self.analyze_do_while_statement(statement)
            return
        if isinstance(statement, WhileStatement):
            self.analyze_while_statement(statement)
            return
        if isinstance(statement, IfStatement):
            self.analyze_if_statement(statement)
            return
        if isinstance(statement, ReturnStatement):
            self.analyze_return_statement(statement)
            return
        if isinstance(statement, ArrayDeclaration):
            self.analyze_array_declaration(statement)
            return
        if isinstance(statement, ArrayAssignment):
            self.analyze_array_assignment(statement)
            return
        if isinstance(statement, ConstantDeclaration):
            self.analyze_constant_declaration(statement)
            return
        if isinstance(statement, VariableDeclaration):
            self.analyze_variable_declaration(statement)
            return
        if isinstance(statement, Assignment):
            self.analyze_assignment(statement)
            return
        if isinstance(statement, FunctionCall):
            self.analyze_function_call(statement)
            return
        raise SemanticError(f"Unsupported statement: {type(statement).__name__}")

    def resolve_type(self, type_name):
        seen = set()
        while type_name in self.aliases:
            if type_name in seen:
                raise SemanticError(
                    f"Circular type alias '{type_name}'"
                )
            seen.add(type_name)
            type_name = self.aliases[type_name]
        return type_name
        # Resolve canonical aliased type

    def register_alias(self, declaration):
        if declaration.name in self.types or declaration.name in self.aliases:
            raise SemanticError(
                f"Type '{declaration.name}' is already declared"
            )

        target = self.resolve_type(declaration.target_type)
        primitive_types = {
            "int", "double", "bool", "char", "string", "bytes",
            "short", "ushort", "uint", "long", "ulong",
            "llong", "ullong", "long_double",
            "i8", "i16", "i32", "i64", "i128",
            "u8", "u16", "u32", "u64", "u128",
            "f32", "f64",
        }
        if target not in primitive_types and target not in self.types:
            raise SemanticError(
                f"Unknown type '{declaration.target_type}'"
            )
        self.aliases[declaration.name] = declaration.target_type
        # Register equivalent type name

    def analyze_switch_statement(self, statement):
        switch_type = self.resolve_type(
            self.analyze_expression(statement.expression)
        )
        if is_numeric_type(switch_type):
            switch_type = canonical_numeric_type(switch_type)

        seen_values = set()
        for case in statement.cases:
            case_type = self.resolve_type(
                self.analyze_expression(case.value)
            )
            if is_numeric_type(case_type):
                case_type = canonical_numeric_type(case_type)
            if case_type != switch_type:
                raise SemanticError(
                    "Case value type must match selected type"
                )
            literal_value = getattr(case.value, "value", None)
            literal_key = (case_type, literal_value)
            if literal_value is not None and literal_key in seen_values:
                raise SemanticError("Duplicate case value")
            if literal_value is not None:
                seen_values.add(literal_key)
            self.analyze_scoped_block(case.body)

        self.analyze_scoped_block(statement.default_body)
        # Validate isolated value branches

    def register_composite(self, definition, immutable):
        if definition.name in self.types:
            raise SemanticError(
                f"Type '{definition.name}' is already declared"
            )
        names = [field.name for field in definition.fields]
        if len(names) != len(set(names)):
            raise SemanticError(
                f"Duplicate field in '{definition.name}'"
            )
        self.types[definition.name] = {
            "kind": "record" if immutable else "struct",
            "fields": definition.fields,
            "immutable": immutable,
        }

    def register_enum(self, definition):
        if definition.name in self.types:
            raise SemanticError(f"Type '{definition.name}' is already declared")
        names = [m.name for m in definition.members]
        if len(names) != len(set(names)):
            raise SemanticError(f"Duplicate enum member in '{definition.name}'")
        self.types[definition.name] = {"kind": "enum", "members": definition.members}

    def analyze_match_statement(self, statement):
        enum_type = self.resolve_type(self.analyze_expression(statement.expression))
        if enum_type not in self.types or self.types[enum_type]["kind"] != "enum":
            raise SemanticError("Match requires an enum value")
        variants = {m.name: m for m in self.types[enum_type]["members"]}
        seen = set()
        for arm in statement.arms:
            if arm.variant_name not in variants:
                raise SemanticError(f"Unknown match variant '{arm.variant_name}'")
            if arm.variant_name in seen:
                raise SemanticError(f"Duplicate match variant '{arm.variant_name}'")
            seen.add(arm.variant_name)
            variant = variants[arm.variant_name]
            if len(arm.bindings) != len(variant.payload_types):
                raise SemanticError(f"Variant '{arm.variant_name}' expects {len(variant.payload_types)} bindings")
            saved = dict(self.variables)
            for name, value_type in zip(arm.bindings, variant.payload_types): self.variables[name] = value_type
            for child in arm.body: self.analyze_statement(child)
            self.variables = saved
        if not statement.default_body and seen != set(variants):
            missing = ", ".join(sorted(set(variants)-seen))
            raise SemanticError(f"Non-exhaustive match; missing: {missing}")
        self.analyze_scoped_block(statement.default_body)


    def analyze_object_declaration(self, declaration):
        if declaration.type_name not in self.types:
            raise SemanticError(
                f"Unknown type '{declaration.type_name}'"
            )
        info = self.types[declaration.type_name]
        if info["kind"] == "enum":
            raise SemanticError(
                "Enum values use qualified members"
            )
        fields = info["fields"]
        if info["kind"] == "class":
            constructor = info["constructor"]
            parameters = constructor.parameters if constructor else []
            if len(declaration.arguments) != len(parameters):
                raise SemanticError(f"Constructor for '{declaration.type_name}' expects {len(parameters)} arguments")
            for parameter, argument in zip(parameters, declaration.arguments):
                if not self.types_compatible(parameter.var_type, self.analyze_expression(argument)):
                    raise SemanticError(f"Invalid constructor argument '{parameter.name}'")
            self.objects[declaration.name] = declaration.type_name
            self.variables[declaration.name] = declaration.type_name
            return
        if len(fields) != len(declaration.arguments):
            raise SemanticError(
                f"Type '{declaration.type_name}' requires {len(fields)} values"
            )
        for field, argument in zip(fields, declaration.arguments):
            if not self.types_compatible(field.field_type, self.analyze_expression(argument)):
                raise SemanticError(
                    f"Invalid value for field '{field.name}'"
                )
        self.objects[declaration.name] = declaration.type_name
        self.variables[declaration.name] = declaration.type_name

    def analyze_member_assignment(self, assignment):
        if assignment.object_name not in self.objects:
            raise SemanticError(
                f"Unknown object '{assignment.object_name}'"
            )
        type_name = self.objects[assignment.object_name]
        info = self.types[type_name]
        if info["immutable"]:
            raise SemanticError(
                f"Record '{type_name}' is immutable"
            )
        field = next(
            (f for f in info["fields"] if f.name == assignment.member_name),
            None,
        )
        if field is None:
            raise SemanticError(
                f"Unknown field '{assignment.member_name}'"
            )
        if not self.types_compatible(field.field_type, self.analyze_expression(assignment.value)):
            raise SemanticError(
                f"Invalid value for field '{assignment.member_name}'"
            )

    def types_compatible(self, expected, actual):
        expected = self.resolve_type(expected)
        actual = self.resolve_type(actual)

        # Optional values cannot flow into a non-optional destination.
        # A present value can be safely promoted to an optional destination.
        # Full absence/presence tracking is deliberately not enabled yet.
        if expected.endswith("?") or actual.endswith("?"):
            if not expected.endswith("?"):
                return False
            expected_base = expected[:-1]
            actual_base = actual[:-1] if actual.endswith("?") else actual
            return self.types_compatible(expected_base, actual_base)

        expected_numeric = canonical_numeric_type(expected)
        actual_numeric = canonical_numeric_type(actual)

        if expected == actual or expected_numeric == actual_numeric:
            return True

        if is_integer_type(expected_numeric) and is_integer_type(actual_numeric):
            return integer_conversion_is_safe(actual_numeric, expected_numeric)

        if is_float_type(expected_numeric):
            if is_integer_type(actual_numeric):
                return True
            if is_float_type(actual_numeric):
                return FLOAT_BITS[actual_numeric] <= FLOAT_BITS[expected_numeric]

        return False
        # Check safe implicit conversions

    def analyze_scoped_block(self, statements):
        previous_variables = self.variables
        previous_arrays = self.arrays
        self.variables = dict(self.variables)
        self.arrays = dict(self.arrays)
        try:
            with self.lexical_bindings.scoped():
                for statement in statements:
                    self.analyze_statement(statement)
        finally:
            self.variables = previous_variables
            self.arrays = previous_arrays
        # Analyze isolated lexical block

    def block_guarantees_return(self, statements):
        for statement in statements:
            if isinstance(statement, ReturnStatement):
                return True
            if isinstance(statement, WithFileStatement) and self.block_guarantees_return(statement.body):
                return True
            if isinstance(statement, IfStatement):
                if (
                    statement.else_body
                    and self.block_guarantees_return(statement.then_body)
                    and self.block_guarantees_return(statement.else_body)
                ):
                    return True
        return False
        # Check guaranteed function return

    def register_function(self, function):
        if function.name in self.functions:
            raise SemanticError(
                f"Function '{function.name}' is already declared"
            )

        seen_default = False
        parameter_names = set()
        for parameter in function.parameters:
            if parameter.name in parameter_names:
                raise SemanticError(
                    f"Parameter '{parameter.name}' is already declared"
                )
            parameter_names.add(parameter.name)
            if parameter.default_value is not None:
                seen_default = True
                default_type = self.analyze_expression(parameter.default_value)
                if not self.types_compatible(parameter.var_type, default_type):
                    raise SemanticError(
                        f"Default value for parameter '{parameter.name}' "
                        f"expects '{parameter.var_type}', received '{default_type}'"
                    )
            elif seen_default:
                raise SemanticError(
                    "Required parameter cannot follow a default parameter"
                )

        self.functions[function.name] = {
            "arguments": len(function.parameters),
            "required_arguments": sum(parameter.default_value is None for parameter in function.parameters),
            "return_type": function.return_type,
            "parameter_types": [parameter.var_type for parameter in function.parameters],
            "parameter_names": [parameter.name for parameter in function.parameters],
            "default_values": [parameter.default_value for parameter in function.parameters],
        }
        # Register function signature

    def analyze_function_definition(self, function):
        global_variables = self.variables
        global_arrays = self.arrays
        global_objects = self.objects
        previous_return_type = self.current_return_type

        self.variables = {}
        self.arrays = {}
        self.objects = {}
        self.current_return_type = function.return_type

        try:
            with self.lexical_bindings.function_scoped():
                for parameter in function.parameters:
                    try:
                        self.lexical_bindings.declare(parameter.name)
                    except DuplicateBindingError as exc:
                        raise SemanticError(
                            f"Parameter '{parameter.name}' is already declared"
                        ) from exc
                    self.variables[parameter.name] = parameter.var_type

                for statement in function.body:
                    self.analyze_statement(statement)
        finally:
            self.variables = global_variables
            self.arrays = global_arrays
            self.objects = global_objects
            self.current_return_type = previous_return_type

        if (
            function.return_type != "void"
            and not self.block_guarantees_return(function.body)
        ):
            raise SemanticError(
                f"Function '{function.name}' must return '{function.return_type}'"
            )
        # Analyze typed function scope


    def analyze_for_statement(self, statement):
        start_type = self.analyze_expression(
            statement.start
        )

        if not is_integer_type(start_type):
            raise SemanticError(
                "For counter start must be integer"
            )

        if statement.counter_name not in self.variables:
            self.variables[statement.counter_name] = "int"
        elif not is_integer_type(self.variables[statement.counter_name]):
            raise SemanticError(
                "For counter must be integer"
            )

        comparison = statement.comparison

        if not isinstance(comparison, BinaryOperation):
            raise SemanticError(
                "For condition must be a comparison"
            )

        if comparison.operator not in {
            "<",
            "<=",
            ">",
            ">=",
        }:
            raise SemanticError(
                "For condition requires <, <=, >, or >="
            )

        if not isinstance(comparison.left, Variable):
            raise SemanticError(
                "For condition must use counter on left"
            )

        if comparison.left.name != statement.counter_name:
            raise SemanticError(
                "For condition must use the same counter"
            )

        condition_type = self.analyze_expression(
            comparison
        )

        if condition_type != "bool":
            raise SemanticError(
                "For condition must be boolean"
            )

        if statement.step <= 0:
            raise SemanticError(
                "For step must be greater than zero"
            )

        expected_direction = (
            1 if comparison.operator in {"<", "<="} else -1
        )
        if (
            statement.direction != 0
            and statement.direction != expected_direction
        ):
            raise SemanticError(
                "Incoherent for direction"
            )

        self.loop_depth += 1
        try:
            for child in statement.body:
                self.analyze_statement(child)
        finally:
            self.loop_depth -= 1
        # Validate counter loop statement

    def analyze_do_while_statement(self, statement):
        self.loop_depth += 1
        try:
            for child in statement.body:
                self.analyze_statement(child)
        finally:
            self.loop_depth -= 1

        condition_type = self.analyze_expression(
            statement.condition
        )
        if not self.is_condition_type(condition_type):
            raise SemanticError(
                "Do-while condition must be boolean, numeric, char, or string"
            )
        # Validate post-test loop statement

    def analyze_while_statement(self, statement):
        condition_type = self.analyze_expression(
            statement.condition
        )

        if not self.is_condition_type(condition_type):
            raise SemanticError(
                "While condition must be boolean, numeric, char, or string"
            )

        if (
            isinstance(statement.condition, Boolean)
            and statement.condition.value
            and not self.block_has_loop_exit(statement.body)
        ):
            raise SemanticError(
                "Infinite loop: while condition is always true and has no exit"
            )

        self.loop_depth += 1
        try:
            if self.allow_lexical_shadowing:
                self.analyze_scoped_block(statement.body)
            else:
                for child in statement.body:
                    self.analyze_statement(child)
        finally:
            self.loop_depth -= 1
        # Validate while loop statement

    def analyze_loop_statement(self, statement):
        if not self.block_has_loop_exit(statement.body):
            raise SemanticError(
                "Infinite loop: explicit loop has no exit"
            )
        self.loop_depth += 1
        try:
            for child in statement.body:
                self.analyze_statement(child)
        finally:
            self.loop_depth -= 1
        # Validate explicit infinite loop

    def block_has_loop_exit(self, statements):
        for statement in statements:
            if isinstance(statement, (BreakStatement, ReturnStatement)):
                return True
            if isinstance(statement, IfStatement):
                if (
                    self.block_has_loop_exit(statement.then_body)
                    or self.block_has_loop_exit(statement.else_body)
                ):
                    return True
        return False
        # Find structurally possible loop exit

    def is_condition_type(self, type_name):
        type_name = self.resolve_type(type_name)
        return (
            type_name == "bool"
            or type_name in INTEGER_BITS
            or type_name in FLOAT_BITS
            or type_name in ("char", "string")
        )
        # Accept defined truthy value types

    def analyze_if_statement(self, statement):
        condition_type = self.analyze_expression(
            statement.condition
        )

        if not self.is_condition_type(condition_type):
            raise SemanticError(
                "If condition must be boolean, numeric, char, or string"
            )

        self.analyze_scoped_block(statement.then_body)
        self.analyze_scoped_block(statement.else_body)
        # Validate scoped conditional statement

    def analyze_return_statement(self, statement):
        if self.current_return_type is None:
            raise SemanticError(
                "Return statement outside function"
            )

        if self.current_return_type == "void":
            if statement.value is not None:
                raise SemanticError(
                    "Void function cannot return a value"
                )
            return

        if statement.value is None:
            raise SemanticError(
                f"Function returning '{self.current_return_type}' "
                "requires a return value"
            )

        value_type = self.analyze_expression(
            statement.value
        )
        if not self.types_compatible(
            self.current_return_type,
            value_type,
        ):
            raise SemanticError(
                f"Cannot return '{value_type}' from "
                f"'{self.current_return_type}' function"
            )
        # Validate function return type


    def analyze_array_declaration(self, declaration):
        if declaration.name in self.variables or declaration.name in self.arrays:
            raise SemanticError(
                f"Name '{declaration.name}' is already declared"
            )
        if not declaration.dynamic and declaration.size <= 0:
            raise SemanticError(
                "Array size must be greater than zero"
            )
        if declaration.second_size is not None and declaration.second_size <= 0:
            raise SemanticError(
                "Array size must be greater than zero"
            )

        capacity = (
            len(declaration.initial_values or [])
            if declaration.dynamic
            else declaration.size
        )
        if declaration.second_size is not None:
            capacity *= declaration.second_size

        if declaration.initial_values is not None:
            if not declaration.dynamic and len(declaration.initial_values) != capacity:
                raise SemanticError(
                    f"Array initializer requires {capacity} values"
                )
            for value in declaration.initial_values:
                value_type = self.analyze_expression(value)
                if not self.types_compatible(
                    declaration.element_type,
                    value_type,
                ):
                    raise SemanticError(
                        "Invalid array initializer value"
                    )

        self.arrays[declaration.name] = {
            "element_type": declaration.element_type,
            "size": declaration.size,
            "second_size": declaration.second_size,
            "dynamic": declaration.dynamic,
        }
        # Register typed array


    def analyze_array_assignment(self, assignment):
        if assignment.name not in self.arrays:
            raise SemanticError(
                f"Array '{assignment.name}' is not declared"
            )
        index_type = self.resolve_type(
            self.analyze_expression(assignment.index)
        )
        if not is_integer_type(canonical_numeric_type(index_type)):
            raise SemanticError("Array index must be int")

        info = self.arrays[assignment.name]
        self.check_fixed_array_index(info, assignment.index, 1)
        if assignment.second_index is not None:
            self.check_fixed_array_index(info, assignment.second_index, 2)
            if info["second_size"] is None:
                raise SemanticError(
                    "Second index requires multidimensional array"
                )
            second_type = self.resolve_type(
                self.analyze_expression(assignment.second_index)
            )
            if not is_integer_type(canonical_numeric_type(second_type)):
                raise SemanticError("Array index must be int")

        value_type = self.analyze_expression(assignment.value)
        if not self.types_compatible(info["element_type"], value_type):
            raise SemanticError(
                f"Cannot assign '{value_type}' to "
                f"'{info['element_type']}' array element"
            )
        # Validate array element assignment


    def check_fixed_array_index(self, info, expression, dimension):
        """Reject provably invalid constant indices; defer dynamic indices to runtime."""
        if info["dynamic"]:
            return
        bound = info["size"] if dimension == 1 else info["second_size"]
        if bound is None:
            return
        index = self.constant_integer_value(expression)
        if index is not None and not 0 <= index < bound:
            raise SemanticError(
                f"Array index out of bounds: {index} for dimension {dimension} (size {bound})"
            )

    def constant_integer_value(self, expression):
        if isinstance(expression, Integer):
            return expression.value
        if (
            isinstance(expression, UnaryOperation)
            and expression.operator == "-"
            and isinstance(expression.operand, Integer)
        ):
            return -expression.operand.value
        return None
        # Return compile-time integer literal

    def validate_integer_literal_range(self, declared_type, expression):
        canonical = canonical_numeric_type(
            self.resolve_type(declared_type)
        )
        if canonical not in INTEGER_BITS:
            return

        value = self.constant_integer_value(expression)
        if value is None:
            return

        minimum, maximum = integer_range(canonical)
        if value > maximum:
            raise SemanticError(
                f"Overflow error: value {value} exceeds {declared_type}"
            )
        if value < minimum:
            raise SemanticError(
                f"Underflow error: value {value} is below {declared_type}"
            )
        # Validate fixed-width literal range

    def analyze_constant_declaration(self, declaration):
        if (
            declaration.name in self.variables
            or declaration.name in self.arrays
            or declaration.name in self.constants
        ):
            raise SemanticError(
                f"Variable '{declaration.name}' is already declared"
            )

        value_type = self.analyze_expression(declaration.value)
        declared_type = declaration.var_type or value_type

        self.validate_integer_literal_range(
            declared_type,
            declaration.value,
        )

        literal_integer = self.constant_integer_value(declaration.value) is not None
        literal_float = isinstance(declaration.value, Double)
        contextual_literal = (
            literal_integer and is_integer_type(
                canonical_numeric_type(self.resolve_type(declared_type))
            )
        ) or (
            literal_float and is_float_type(
                canonical_numeric_type(self.resolve_type(declared_type))
            )
        )

        if not contextual_literal and not self.types_compatible(declared_type, value_type):
            raise SemanticError(
                f"Cannot assign '{value_type}' to '{declared_type}'"
            )

        self.variables[declaration.name] = declared_type
        self.constants.add(declaration.name)
        # Register immutable typed constant

    def analyze_variable_declaration(self, declaration):
        # A nested explicit declaration may shadow a visible outer variable.
        # Duplicate declarations in the current lexical frame remain invalid.
        if (
            declaration.name in self.arrays
            or self.lexical_bindings.is_declared_here(declaration.name)
            or (
                (not self.allow_lexical_shadowing or self.lexical_bindings.depth == 0)
                and declaration.name in self.variables
            )
        ):
            raise SemanticError(
                f"Variable '{declaration.name}' is already declared"
            )

        value_type = self.analyze_expression(declaration.value)
        self.validate_integer_literal_range(
            declaration.var_type,
            declaration.value,
        )

        target = canonical_numeric_type(
            self.resolve_type(declaration.var_type)
        )
        contextual_literal = (
            self.constant_integer_value(declaration.value) is not None
            and is_integer_type(target)
        ) or (
            isinstance(declaration.value, Double)
            and is_float_type(target)
        )

        text_char_literal = (
            declaration.var_type == "char"
            and isinstance(declaration.value, String)
            and len(declaration.value.value) <= 1
        )
        if not contextual_literal and not text_char_literal and not self.types_compatible(
            declaration.var_type, value_type
        ):
            expected_numeric = canonical_numeric_type(self.resolve_type(declaration.var_type))
            actual_numeric = canonical_numeric_type(self.resolve_type(value_type))
            if is_numeric_type(expected_numeric) and is_numeric_type(actual_numeric):
                raise SemanticError(
                    f"Precision loss: cannot implicitly convert '{value_type}' to '{declaration.var_type}'"
                )
            raise SemanticError(
                f"Cannot assign '{value_type}' to '{declaration.var_type}'"
            )

        # Commit both symbol tables only after validation succeeds. A failed
        # declaration must not leave a partially registered variable.
        if self.lexical_bindings.is_declared_here(declaration.name):
            raise SemanticError(f"Variable '{declaration.name}' is already declared")
        self.lexical_bindings.declare(declaration.name)
        self.variables[declaration.name] = declaration.var_type

    def analyze_assignment(self, assignment):
        if assignment.name in self.constants:
            raise SemanticError(
                f"Cannot assign to constant '{assignment.name}'"
            )

        value_type = self.analyze_expression(assignment.value)

        if assignment.name not in self.variables:
            # An inferred first assignment introduces a binding in this scope.
            # Reassignments of visible names retain the original identity.
            if self.lexical_bindings.is_declared_here(assignment.name):
                raise SemanticError(f"Variable '{assignment.name}' is already declared")
            self.lexical_bindings.declare(assignment.name)
            self.variables[assignment.name] = value_type
            return

        variable_type = self.variables[assignment.name]
        self.validate_integer_literal_range(
            variable_type,
            assignment.value,
        )

        text_char_literal = (
            variable_type == "char"
            and isinstance(assignment.value, String)
            and len(assignment.value.value) <= 1
        )
        if not text_char_literal and not self.types_compatible(variable_type, value_type):
            expected_numeric = canonical_numeric_type(self.resolve_type(variable_type))
            actual_numeric = canonical_numeric_type(self.resolve_type(value_type))
            if is_numeric_type(expected_numeric) and is_numeric_type(actual_numeric):
                raise SemanticError(
                    f"Precision loss: cannot implicitly convert '{value_type}' to '{variable_type}'"
                )
            raise SemanticError(
                f"Cannot assign '{value_type}' to '{variable_type}'"
            )

    def analyze_expression(self, expression):
        if isinstance(expression, TupleLiteral):
            for value in expression.values: self.analyze_expression(value)
            return "tuple"
        if isinstance(expression, VariantConstructor) and self.variables.get(expression.enum_name) in ("file_handle", "file_handle_binary"):
            return self.analyze_function_call(FunctionCall(
                expression.enum_name + "." + expression.variant_name, expression.arguments,
            ))
        if isinstance(expression, VariantConstructor) and expression.enum_name in {"File", "Directory", "Path", "Bytes", "Console"}:
            return self.analyze_function_call(FunctionCall(
                expression.enum_name + "." + expression.variant_name, expression.arguments,
            ))
        if isinstance(expression, VariantConstructor):
            qualified_name = expression.enum_name + "." + expression.variant_name
            if qualified_name in self.functions:
                return self.analyze_function_call(FunctionCall(qualified_name, expression.arguments))
            if expression.enum_name in self.objects:
                return self.analyze_function_call(FunctionCall(
                    expression.enum_name + "." + expression.variant_name,
                    expression.arguments,
                ))
            if expression.enum_name not in self.types or self.types[expression.enum_name]["kind"] != "enum":
                raise SemanticError(f"Unknown enum '{expression.enum_name}'")
            variant = next((m for m in self.types[expression.enum_name]["members"] if m.name == expression.variant_name), None)
            if variant is None: raise SemanticError(f"Unknown enum member '{expression.variant_name}'")
            if len(variant.payload_types) != len(expression.arguments):
                raise SemanticError(f"Variant '{expression.variant_name}' expects {len(variant.payload_types)} values")
            for expected, argument in zip(variant.payload_types, expression.arguments):
                actual=self.analyze_expression(argument)
                if not self.types_compatible(expected, actual): raise SemanticError(f"Invalid payload for variant '{expression.variant_name}'")
            return expression.enum_name
        if isinstance(expression, Char):
            return "char"
        if isinstance(expression, String):
            return "string"
        if isinstance(expression, MemberAccess):
            if self.variables.get(expression.object_name) == "quar_error":
                if expression.member_name in ("message", "cause", "trace"):
                    return "string"
                raise SemanticError("Unknown error field")

            if expression.member_name == "length":
                if expression.object_name in self.arrays:
                    return "int"
                if (
                    expression.object_name in self.variables
                    and self.resolve_type(
                        self.variables[expression.object_name]
                    ) == "string"
                ):
                    return "int"
            if expression.object_name in self.types:
                info = self.types[expression.object_name]
                if info["kind"] != "enum":
                    raise SemanticError(
                        "Qualified type access requires enum"
                    )
                member_names = [m.name for m in info["members"]]
                if expression.member_name not in member_names:
                    raise SemanticError(
                        f"Unknown enum member '{expression.member_name}'"
                    )
                return expression.object_name
            if expression.object_name in self.objects:
                type_name = self.objects[expression.object_name]
            elif expression.object_name in self.variables:
                type_name = self.resolve_type(
                    self.variables[expression.object_name]
                )
                if type_name.endswith("?"):
                    raise SemanticError(
                        f"Cannot access a member of optional type '{type_name}' without a presence check"
                    )
                if type_name not in self.types:
                    raise SemanticError(
                        f"Unknown object '{expression.object_name}'"
                    )
            else:
                raise SemanticError(
                    f"Unknown object '{expression.object_name}'"
                )
            if type_name.endswith("?"):
                raise SemanticError(
                    f"Cannot access a member of optional type '{type_name}' without a presence check"
                )
            info = self.types[type_name]
            field = next(
                (f for f in info["fields"] if f.name == expression.member_name),
                None,
            )
            if field is None:
                raise SemanticError(
                    f"Unknown field '{expression.member_name}'"
                )
            return field.field_type
        if isinstance(expression, Integer):
            return "int"
        if isinstance(expression, Double):
            return "double"
        if isinstance(expression, Boolean):
            return "bool"
        if isinstance(expression, ArrayAccess):
            index_type = self.resolve_type(
                self.analyze_expression(expression.index)
            )
            if not is_integer_type(canonical_numeric_type(index_type)):
                raise SemanticError("Sequence index must be int")

            if expression.name in self.arrays:
                info = self.arrays[expression.name]
                self.check_fixed_array_index(info, expression.index, 1)
                if expression.second_index is not None:
                    self.check_fixed_array_index(info, expression.second_index, 2)
                    if info["second_size"] is None:
                        raise SemanticError(
                            "Second index requires multidimensional array"
                        )
                    second_type = self.resolve_type(
                        self.analyze_expression(expression.second_index)
                    )
                    if not is_integer_type(canonical_numeric_type(second_type)):
                        raise SemanticError("Array index must be int")
                return info["element_type"]

            if (
                expression.name in self.variables
                and self.resolve_type(
                    self.variables[expression.name]
                ) == "string"
            ):
                if expression.second_index is not None:
                    raise SemanticError(
                        "String accepts one index"
                    )
                return "char"

            if (
                expression.name in self.variables
                and self.resolve_type(self.variables[expression.name]) == "bytes"
            ):
                if expression.second_index is not None:
                    raise SemanticError("Bytes accepts one index")
                return "int"

            raise SemanticError(
                f"Sequence '{expression.name}' is not declared"
            )
        if isinstance(expression, Variable):
            if expression.name not in self.variables:
                raise SemanticError(
                    f"Variable '{expression.name}' is not declared"
                )
            return self.variables[expression.name]
        if isinstance(expression, UnaryOperation):
            return self.analyze_unary_operation(expression)
        if isinstance(expression, BinaryOperation):
            return self.analyze_binary_operation(expression)
        if isinstance(expression, FunctionCall):
            return self.analyze_function_call(expression)
        raise SemanticError(f"Unsupported expression: {type(expression).__name__}")

    def analyze_unary_operation(self, expression):
        operand_type = self.analyze_expression(
            expression.operand
        )

        if self.resolve_type(operand_type).endswith("?"):
            raise SemanticError(
                f"Cannot apply unary operator to optional type '{operand_type}' without a presence check"
            )

        if expression.operator == "not":
            if operand_type != "bool":
                raise SemanticError(
                    "Logical NOT operand must be boolean"
                )
            return "bool"

        if expression.operator == "-":
            if not is_numeric_type(
                canonical_numeric_type(operand_type)
            ):
                raise SemanticError(
                    "Unary minus operand must be numeric"
                )
            return operand_type

        if expression.operator == "~":
            canonical = canonical_numeric_type(operand_type)
            if canonical not in INTEGER_BITS:
                raise SemanticError(
                    "Bitwise NOT operand must be integer"
                )
            return canonical

        raise SemanticError(
            f"Unsupported unary operator '{expression.operator}'"
        )

    def analyze_binary_operation(self, expression):
        left_type = self.analyze_expression(expression.left)
        right_type = self.analyze_expression(expression.right)
        if self.resolve_type(left_type).endswith("?") or self.resolve_type(right_type).endswith("?"):
            raise SemanticError(
                "Optional values cannot be used in binary operations without a presence check"
            )
        numeric_types = {
            "int", "double", "short", "ushort", "uint",
            "long", "ulong", "llong", "ullong", "long_double",
            "i8", "i16", "i32", "i64", "i128",
            "u8", "u16", "u32", "u64", "u128",
            "f32", "f64",
        }
        arithmetic_operators = {"+", "-", "*", "/", "%"}
        bitwise_operators = {"&", "|", "^", "<<", ">>"}
        comparison_operators = {
            "==",
            "!=",
            "<",
            "<=",
            ">",
            ">=",
        }
        logical_operators = {"and", "or"}

        if expression.operator == "+" and (
            left_type == "string" and right_type == "string"
        ):
            return "string"

        if expression.operator in arithmetic_operators:
            if left_type not in numeric_types:
                raise SemanticError(
                    "Left operand must be numeric"
                )
            if right_type not in numeric_types:
                raise SemanticError(
                    "Right operand must be numeric"
                )
            left_canonical = canonical_numeric_type(left_type)
            right_canonical = canonical_numeric_type(right_type)

            if is_float_type(left_canonical) or is_float_type(right_canonical):
                float_types = [
                    t for t in (left_canonical, right_canonical)
                    if is_float_type(t)
                ]
                return max(float_types, key=lambda t: FLOAT_BITS[t])

            if left_canonical == right_canonical:
                return left_canonical

            if integer_conversion_is_safe(left_canonical, right_canonical):
                return right_canonical
            if integer_conversion_is_safe(right_canonical, left_canonical):
                return left_canonical

            raise SemanticError(
                "Numeric operation requires explicit conversion"
            )

        if expression.operator in bitwise_operators:
            left_canonical = canonical_numeric_type(left_type)
            right_canonical = canonical_numeric_type(right_type)
            if left_canonical not in INTEGER_BITS:
                raise SemanticError(
                    "Left bitwise operand must be integer"
                )
            if right_canonical not in INTEGER_BITS:
                raise SemanticError(
                    "Right bitwise operand must be integer"
                )
            if expression.operator in {"<<", ">>"}:
                return left_canonical
            if left_canonical == right_canonical:
                return left_canonical
            if integer_conversion_is_safe(left_canonical, right_canonical):
                return right_canonical
            if integer_conversion_is_safe(right_canonical, left_canonical):
                return left_canonical
            raise SemanticError(
                "Bitwise operation requires explicit conversion"
            )

        if expression.operator in {"==", "!="} and (
            left_type == "bytes" or right_type == "bytes"
        ):
            if left_type != right_type:
                raise SemanticError("Bytes comparison requires matching bytes types")
            return "bool"

        if expression.operator in comparison_operators:
            if left_type in {"string", "char"} or right_type in {"string", "char"}:
                if left_type != right_type:
                    raise SemanticError("Text comparison requires matching text types")
                return "bool"
            if left_type == "bool" or right_type == "bool":
                if expression.operator not in {"==", "!="} or left_type != right_type:
                    raise SemanticError("Boolean comparison supports matching == or != operands")
                return "bool"
            if left_type not in numeric_types:
                raise SemanticError(
                    "Left comparison operand must be numeric"
                )
            if right_type not in numeric_types:
                raise SemanticError(
                    "Right comparison operand must be numeric"
                )
            return "bool"

        if expression.operator in logical_operators:
            if left_type != "bool":
                raise SemanticError(
                    "Left logical operand must be boolean"
                )
            if right_type != "bool":
                raise SemanticError(
                    "Right logical operand must be boolean"
                )
            return "bool"

        raise SemanticError(
            f"Unsupported operator '{expression.operator}'"
        )

    def analyze_function_call(self, call):
        if "." in call.name:
            handle, method = call.name.split(".", 1)
            if self.variables.get(handle) in ("file_handle", "file_handle_binary"):
                content_type = "bytes" if self.variables[handle] == "file_handle_binary" else "string"
                methods = {"read_all": ([], content_type), "read_line": ([], content_type),
                           "write": ([content_type], "void"), "seek": (["int"], "void")}
                if method not in methods:
                    raise SemanticError(f"Unknown file method '{method}'")
                expected, result = methods[method]
                if len(call.arguments) != len(expected):
                    raise SemanticError(f"File method '{method}' expects {len(expected)} arguments")
                for arg, required in zip(call.arguments, expected):
                    if self.analyze_expression(arg) != required:
                        raise SemanticError(f"File method '{method}' expects '{required}'")
                return result

        file_operations = {
            "File.read_text": (["string"], "string"),
            "File.write_text": (["string", "string"], "void"),
            "File.write_text_atomic": (["string", "string"], "void"),
            "File.append_text": (["string", "string"], "void"),
            "File.exists": (["string"], "bool"),
            "File.delete": (["string"], "void"),
            "File.copy": (["string", "string"], "void"),
            "File.move": (["string", "string"], "void"),
            "Directory.create": (["string"], "void"),
            "Directory.exists": (["string"], "bool"),
            "Directory.delete": (["string"], "void"),
            "Path.join": (["string", "string"], "string"),
            "Path.name": (["string"], "string"),
            "Path.parent": (["string"], "string"),
            "File.size": (["string"], "int"),
            "File.read_line": (["string", "int"], "string"),
            "File.read_range": (["string", "int", "int"], "string"),
            "Directory.count": (["string"], "int"),
            "Directory.create_all": (["string"], "void"),
            "File.line_count": (["string"], "int"),
            "File.read_bytes": (["string"], "bytes"),
            "File.write_bytes": (["string", "bytes"], "void"),
            "File.write_bytes_atomic": (["string", "bytes"], "void"),
            "File.append_bytes": (["string", "bytes"], "void"),
            "File.read_bytes_range": (["string", "int", "int"], "bytes"),
            "Bytes.from_hex": (["string"], "bytes"),
            "Bytes.to_hex": (["bytes"], "string"),
            "Bytes.length": (["bytes"], "int"),
            "File.read_bytes_hex": (["string"], "string"),
            "File.write_bytes_hex": (["string", "string"], "void"),
            "File.append_bytes_hex": (["string", "string"], "void"),
            "File.read_bytes_hex_range": (["string", "int", "int"], "string"),
            "Directory.is_empty": (["string"], "bool"),
            "Directory.list_text": (["string"], "string"),
            "Directory.entry": (["string", "int"], "string"),
            "Directory.entry_is_file": (["string", "int"], "bool"),
            "Directory.entry_is_directory": (["string", "int"], "bool"),
            "Path.suffix": (["string"], "string"),
            "Path.stem": (["string"], "string"),
            "Path.absolute": (["string"], "string"),
            "Path.normalize": (["string"], "string"),
        }
        if call.name in file_operations:
            expected, result = file_operations[call.name]
            if len(call.arguments) != len(expected):
                raise SemanticError(f"'{call.name}' expects {len(expected)} arguments")
            for argument, required in zip(call.arguments, expected):
                actual = self.resolve_type(self.analyze_expression(argument))
                if actual != self.resolve_type(required):
                    raise SemanticError(f"'{call.name}' expects '{required}', received '{actual}'")
            return result
        if "." in call.name:
            object_name, method_name = call.name.split(".", 1)
            if object_name in self.objects:
                type_name = self.objects[object_name]
                info = self.types[type_name]
                if info["kind"] != "class":
                    raise SemanticError(f"Type '{type_name}' has no methods")
                method = info["methods"].get(method_name)
                if method is None:
                    raise SemanticError(f"Unknown method '{method_name}'")
                if len(call.arguments) != len(method.parameters):
                    raise SemanticError(f"Method '{method_name}' argument count mismatch")
                for parameter, argument in zip(method.parameters, call.arguments):
                    if not self.types_compatible(parameter.var_type, self.analyze_expression(argument)):
                        raise SemanticError(f"Invalid method argument '{parameter.name}'")
                return method.return_type
        console_calls = {
            "Console.arg_count": (0, None, "int"),
            "Console.arg": (1, "int", "string"),
            "Console.env": (1, "string", "string"),
            "Console.env_exists": (1, "string", "bool"),
        }
        if call.name in console_calls:
            count, required, result = console_calls[call.name]
            if len(call.arguments) != count:
                raise SemanticError(f"{call.name} expects {count} arguments")
            if required is not None:
                actual = self.resolve_type(self.analyze_expression(call.arguments[0]))
                if required == "int":
                    if not is_integer_type(canonical_numeric_type(actual)):
                        raise SemanticError("Console.arg index must be an integer")
                elif actual != required:
                    raise SemanticError(f"{call.name} argument must be a string")
            return result

        if call.name in {"stdout", "stderr", "exit"}:
            if len(call.arguments) != 1:
                raise SemanticError(f"{call.name} expects exactly one argument")
            actual = self.resolve_type(self.analyze_expression(call.arguments[0]))
            if call.name == "exit":
                if not is_integer_type(canonical_numeric_type(actual)):
                    raise SemanticError("exit code must be an integer")
            elif actual != "string":
                raise SemanticError(f"{call.name} argument must be a string")
            return "void"

        if call.name == "panic":
            if len(call.arguments) != 1:
                raise SemanticError("panic expects one string argument")
            if self.resolve_type(self.analyze_expression(call.arguments[0])) != "string":
                raise SemanticError("panic message must be a string")
            return "void"

        if call.name == "assert":
            if len(call.arguments) != 1:
                raise SemanticError("assert expects one boolean argument")
            if self.resolve_type(self.analyze_expression(call.arguments[0])) != "bool":
                raise SemanticError("assert argument must be a boolean")
            return "void"

        if call.name == "input":
            if len(call.arguments) > 1:
                raise SemanticError("input expects zero or one string argument")
            if call.arguments and self.resolve_type(self.analyze_expression(call.arguments[0])) != "string":
                raise SemanticError("input prompt must be a string")
            return "string"

        string_builtins = {
            "substring": (["string", "int", "int"], "string"),
            "find": (["string", "string"], "int"),
            "replace": (["string", "string", "string"], "string"),
            "trim": (["string"], "string"),
            "to_string": (None, "string"),
            "to_int": (["string"], "int"),
            "to_double": (["string"], "double"),
        }
        if call.name in string_builtins:
            expected, return_type = string_builtins[call.name]
            if expected is None:
                if len(call.arguments) != 1:
                    raise SemanticError("to_string expects one argument")
                self.analyze_expression(call.arguments[0])
                return return_type
            if len(call.arguments) != len(expected):
                raise SemanticError(
                    f"Function '{call.name}' expects {len(expected)} arguments, received {len(call.arguments)}"
                )
            for index, (argument, required) in enumerate(zip(call.arguments, expected), start=1):
                actual = self.resolve_type(self.analyze_expression(argument))
                required_resolved = self.resolve_type(required)
                if required_resolved == "i32":
                    if not is_integer_type(canonical_numeric_type(actual)):
                        raise SemanticError(f"Function '{call.name}' argument {index} must be integer")
                elif actual != required_resolved:
                    raise SemanticError(
                        f"Function '{call.name}' argument {index} expects '{required}', received '{actual}'"
                    )
            return return_type

        if call.name not in self.functions:
            raise SemanticError(f"Unknown function '{call.name}'")

        function = self.functions[call.name]
        parameter_names = function.get("parameter_names")
        if parameter_names is None:
            expected_arguments = function["arguments"]
            if len(call.arguments) != expected_arguments:
                raise SemanticError(
                    f"Function '{call.name}' expects {expected_arguments} arguments, "
                    f"received {len(call.arguments)}"
                )
            argument_types = [self.analyze_expression(argument) for argument in call.arguments]
            parameter_types = function.get("parameter_types")
            if parameter_types is not None:
                for index, (argument_type, parameter_type) in enumerate(zip(argument_types, parameter_types), start=1):
                    if not self.types_compatible(parameter_type, argument_type):
                        raise SemanticError(
                            f"Function '{call.name}' argument {index} expects "
                            f"'{parameter_type}', received '{argument_type}'"
                        )
            return function["return_type"]

        values = [None] * len(parameter_names)
        positional_index = 0
        named_started = False
        for argument in call.arguments:
            if isinstance(argument, NamedArgument):
                named_started = True
                if argument.name not in parameter_names:
                    raise SemanticError(
                        f"Function '{call.name}' has no parameter '{argument.name}'"
                    )
                index = parameter_names.index(argument.name)
                if values[index] is not None:
                    raise SemanticError(
                        f"Argument '{argument.name}' is specified more than once"
                    )
                values[index] = argument.value
                continue
            if named_started:
                raise SemanticError(
                    "Positional argument cannot follow a named argument"
                )
            if positional_index >= len(values):
                raise SemanticError(
                    f"Function '{call.name}' received too many arguments"
                )
            values[positional_index] = argument
            positional_index += 1

        defaults = function["default_values"]
        for index, value in enumerate(values):
            if value is None:
                if defaults[index] is None:
                    raise SemanticError(
                        f"Function '{call.name}' missing required argument "
                        f"'{parameter_names[index]}'"
                    )
                values[index] = defaults[index]

        parameter_types = function["parameter_types"]
        for index, (value, parameter_type) in enumerate(zip(values, parameter_types)):
            argument_type = self.analyze_expression(value)
            if not self.types_compatible(parameter_type, argument_type):
                raise SemanticError(
                    f"Function '{call.name}' argument '{parameter_names[index]}' "
                    f"expects '{parameter_type}', received '{argument_type}'"
                )

        call.arguments = values
        return function["return_type"]
        # Normalize defaults and named arguments

