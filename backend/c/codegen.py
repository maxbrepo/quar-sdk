from frontend.quar.ast_nodes import (
    Integer,
    Double,
    Boolean,
    Variable,
    BinaryOperation,
    VariableDeclaration,
    ConstantDeclaration,
    Assignment,
    FunctionCall,
    FunctionDefinition,
    ReturnStatement,
    IfStatement,
    WhileStatement,
    ForStatement,
    ArrayDeclaration, ArrayAccess, ArrayAssignment,
    UnaryOperation, BreakStatement, ContinueStatement,
)

class CCodeGenerator:

    def __init__(self):
        self.variable_types = {}
        self.declared_names = set()
        self.scope_depth = 0

    def generate(self, program, variable_types=None, *, lexical=False, allow_inference=False):
        inferred_names = set()
        if lexical:
            from frontend.quar.lexical_bytecode import LexicalBytecodeLowerer
            lowerer = LexicalBytecodeLowerer(allow_inference=allow_inference)
            program = lowerer.lower(program)
            inferred_names = lowerer.inferred_storage_names
        self.lexical_inferred_names = inferred_names
        self.variable_types = dict(variable_types or {})
        self.declared_names = set()
        self.scope_depth = 0
        functions = [statement for statement in program
                     if isinstance(statement, FunctionDefinition)]
        statements = [statement for statement in program
                      if not isinstance(statement, FunctionDefinition)]
        lines = ["#include <stdio.h>", "#include <stdint.h>", "#include <stdbool.h>", ""]
        for function in functions:
            lines.append(self.generate_function_definition(function))
            lines.append("")
        lines.append("int main(void) {")
        for statement in statements:
            generated = self.generate_statement(statement)
            lines.append(f"    {generated}")

        lines.append("    return 0;")
        lines.append("}")

        return "\n".join(lines)
        # Return complete generated C source

    @staticmethod
    def c_symbol(name):
        # Map qualified Quar identifiers to valid C identifiers without
        # collisions between dots and underscores.
        return "q_" + "".join(f"{len(part)}_{part}" for part in name.split("."))

    def generate_function_definition(self, function):
        # Function parameters and locals must not leak into another function
        # or into main. Each function starts with its own symbol environment.
        outer_names = self.declared_names
        outer_types = self.variable_types
        outer_depth = self.scope_depth
        self.declared_names = {parameter.name for parameter in function.parameters}
        self.variable_types = {
            **outer_types,
            **{parameter.name: parameter.var_type for parameter in function.parameters},
        }
        self.scope_depth = 0
        try:
            parameters = ", ".join(
                f"{self.get_c_type(parameter.var_type)} {parameter.name}"
                for parameter in function.parameters
            ) or "void"
            lines = [f"{self.get_c_type(function.return_type)} "
                     f"{self.c_symbol(function.name)}({parameters}) {{"]
            for statement in function.body:
                lines.append("    " + self.generate_statement(statement))
            lines.append("}")
            return "\n".join(lines)
        finally:
            self.declared_names = outer_names
            self.variable_types = outer_types
            self.scope_depth = outer_depth

    def generate_scoped_statements(self, statements):
        # A C block owns its declarations; outer bindings remain visible.
        outer_names = self.declared_names.copy()
        outer_types = self.variable_types.copy()
        self.scope_depth += 1
        try:
            return "\n".join(
                "    " + self.generate_statement(child).replace("\n", "\n    ")
                for child in statements
            )
        finally:
            self.scope_depth -= 1
            self.declared_names = outer_names
            self.variable_types = outer_types

    def generate_for_statement(self, statement):
        # The counter is an existing binding; the loop header assigns it.
        # The body has its own lexical scope, as in the QRVM compiler.
        counter = statement.counter_name
        declaration = ""
        if counter not in self.declared_names:
            if counter not in self.lexical_inferred_names:
                raise ValueError(f"Unknown for counter: '{counter}'")
            # A Visual Quar for header can introduce an integer counter.
            # Declare it in the containing C scope, avoiding evaluation of
            # the initial expression twice and preserving its post-loop life.
            self.declared_names.add(counter)
            self.variable_types[counter] = "int"
            declaration = f"int {counter};\n"
        if statement.step <= 0:
            raise ValueError("For step must be positive")
        start = self.generate_expression(statement.start)
        comparison = self.generate_expression(statement.comparison)
        direction = statement.direction
        if direction == 0:
            direction = 1 if statement.comparison.operator in ("<", "<=") else -1
        operator = "+=" if direction > 0 else "-="
        body = self.generate_scoped_statements(statement.body)
        return (
            declaration + f"for ({counter} = {start}; {comparison}; "
            f"{counter} {operator} {statement.step}) {{\n{body}\n}}"
        )

    def generate_statement(self, statement):
        if isinstance(statement, ArrayDeclaration):
            if statement.dynamic or statement.second_size is not None:
                raise ValueError("C backend supports only fixed one-dimensional arrays")
            if statement.name in self.declared_names:
                raise ValueError(f"Duplicate array declaration: '{statement.name}'")
            values = statement.initial_values or []
            size = statement.size if statement.size is not None else len(values)
            if size <= 0 or len(values) > size:
                raise ValueError("Invalid fixed array size or initializer count")
            element_type = self.get_c_type(statement.element_type)
            initializer = (" = {" + ", ".join(self.generate_expression(value) for value in values) + "}") if values else " = {0}"
            self.declared_names.add(statement.name)
            self.variable_types[statement.name] = statement.element_type
            return f"{element_type} {statement.name}[{size}]{initializer};"

        if isinstance(statement, ArrayAssignment):
            if statement.second_index is not None:
                raise ValueError("C backend does not support multidimensional array assignment")
            if statement.name not in self.declared_names:
                raise ValueError(f"Unknown array: '{statement.name}'")
            return f"{statement.name}[{self.generate_expression(statement.index)}] = {self.generate_expression(statement.value)};"

        if isinstance(statement, BreakStatement):
            return "break;"
        if isinstance(statement, ContinueStatement):
            return "continue;"

        if isinstance(statement, ForStatement):
            return self.generate_for_statement(statement)

        if isinstance(statement, WhileStatement):
            condition = self.generate_expression(statement.condition)
            body = self.generate_scoped_statements(statement.body)
            return f"while ({condition}) {{\n{body}\n}}"

        if isinstance(statement, IfStatement):
            condition = self.generate_expression(statement.condition)
            then_body = self.generate_scoped_statements(statement.then_body)
            result = f"if ({condition}) {{\n{then_body}\n}}"
            if statement.else_body:
                else_body = self.generate_scoped_statements(statement.else_body)
                result += f" else {{\n{else_body}\n}}"
            return result

        if isinstance(statement, ReturnStatement):
            if statement.value is None:
                return "return;"
            return f"return {self.generate_expression(statement.value)};"

        if isinstance(statement, (VariableDeclaration, ConstantDeclaration)):
            value = self.generate_expression(statement.value)

            declared_type = statement.var_type or self.variable_types.get(statement.name)
            if declared_type is None:
                raise ValueError(f"Unknown type for declaration: '{statement.name}'")
            c_type = self.get_c_type(declared_type)
            self.variable_types[statement.name] = declared_type
            self.declared_names.add(statement.name)

            qualifier = "const " if isinstance(statement, ConstantDeclaration) else ""
            return (
                f"{qualifier}{c_type} {statement.name} = {value};"
            )

        if isinstance(statement, Assignment):
            # Inferred declarations are represented as assignments in the AST.
            # The validated symbol table distinguishes them from unknown names.
            value = self.generate_expression(statement.value)
            if statement.name not in self.declared_names:
                if statement.name not in self.variable_types:
                    if self.scope_depth == 0 and statement.name not in self.lexical_inferred_names:
                        raise ValueError(f"Unknown assignment target: '{statement.name}'")
                    # The semantic pass validates inferred local declarations,
                    # but does not export block-local types to the C backend.
                    self.variable_types[statement.name] = self.infer_expression_type(statement.value)
                self.declared_names.add(statement.name)
                c_type = self.get_c_type(self.variable_types[statement.name])
                return f"{c_type} {statement.name} = {value};"
            return f"{statement.name} = {value};"

        if isinstance(statement, FunctionCall):
            return self.generate_function_call(
                statement,
                statement_mode=True
            )

        raise ValueError(
            f"Unsupported statement: "
            f"{type(statement).__name__}"
        )

    def generate_expression(self, expression):

        if isinstance(expression, Integer):
            return str(expression.value)
            # Convert integer node to C text

        if isinstance(expression, Boolean):
            return "true" if expression.value else "false"

        if isinstance(expression, Double):
            return repr(expression.value)
            # Convert double node to C text

        if isinstance(expression, Variable):
            return expression.name
            # Return C variable name

        if isinstance(expression, ArrayAccess):
            if expression.second_index is not None:
                raise ValueError("C backend does not support multidimensional array access")
            if expression.name not in self.declared_names:
                raise ValueError(f"Unknown array: '{expression.name}'")
            return f"{expression.name}[{self.generate_expression(expression.index)}]"

        if isinstance(expression, UnaryOperation):
            operator = "!" if expression.operator == "not" else expression.operator
            if operator not in ("-", "+", "!", "~"):
                raise ValueError(f"Unsupported unary operator: '{expression.operator}'")
            return f"({operator}{self.generate_expression(expression.operand)})"

        if isinstance(expression, BinaryOperation):
            left = self.generate_expression(
                expression.left
            )

            right = self.generate_expression(
                expression.right
            )

            operator = {"and": "&&", "or": "||"}.get(
                expression.operator, expression.operator
            )
            return f"({left} {operator} {right})"
            # Return parenthesized C expression

        if isinstance(expression, FunctionCall):
            return self.generate_function_call(
                expression,
                statement_mode=False
            )

        raise ValueError(
            f"Unsupported expression: "
            f"{type(expression).__name__}"
        )

    def get_c_type(self, quar_type):
        # Keep the C backend consistent with the canonical numeric aliases.
        from frontend.quar.numeric_types import canonical_numeric_type
        normalized = canonical_numeric_type(quar_type)
        types = {
            "i8": "int8_t", "i16": "int16_t", "i32": "int32_t",
            "i64": "int64_t", "u8": "uint8_t", "u16": "uint16_t",
            "u32": "uint32_t", "u64": "uint64_t",
            "f32": "float", "f64": "double", "bool": "bool", "void": "void",
        }
        if normalized in types:
            return types[normalized]
        raise ValueError(f"Unsupported Quar type: '{quar_type}'")

    def infer_expression_type(self, expression):
        if isinstance(expression, Boolean):
            return "bool"

        if isinstance(expression, Integer):
            return "int"

        if isinstance(expression, Double):
            return "double"

        if isinstance(expression, Variable):
            return self.variable_types.get(
                expression.name,
                "int"
            )

        if isinstance(expression, ArrayAccess):
            return self.variable_types.get(expression.name, "int")
        if isinstance(expression, UnaryOperation):
            return "bool" if expression.operator in ("!", "not") else self.infer_expression_type(expression.operand)

        if isinstance(expression, BinaryOperation):
            if expression.operator in ("and", "or", "==", "!=", "<", "<=", ">", ">="):
                return "bool"
            left_type = self.infer_expression_type(
                expression.left
            )
            right_type = self.infer_expression_type(
                expression.right
            )

            if "double" in (
                left_type,
                right_type,
            ) or "f64" in (left_type, right_type):
                return "double"

            return "int"

        if isinstance(expression, FunctionCall):
            if expression.name == "sum":
                return "int"

        return "int"
        # Return expression numeric type

    def generate_function_call(
        self,
        call,
        statement_mode=False
    ):

        arguments = [
            self.generate_expression(argument)
            for argument in call.arguments
        ]

        if call.name == "print":

            if len(arguments) != 1:
                raise ValueError(
                    "print requires one argument"
                )

            argument_type = self.infer_expression_type(
                call.arguments[0]
            )

            if argument_type in ("double", "f64", "float", "f32"):
                result = (
                    f'printf("%g\\n", {arguments[0]})'
                )
            elif argument_type == "bool":
                result = f'printf("%s\\n", {arguments[0]} ? "True" : "False")'
            else:
                result = (
                    f'printf("%d\\n", {arguments[0]})'
                )

        elif call.name == "sum":

            if len(arguments) != 2:
                raise ValueError(
                    "sum requires two arguments"
                )

            result = (
                f"({arguments[0]} + {arguments[1]})"
            )

        else:
            result = (
                f"{self.c_symbol(call.name)}({', '.join(arguments)})"
            )

        if statement_mode:
            return result + ";"

        return result
        # Return generated C function call