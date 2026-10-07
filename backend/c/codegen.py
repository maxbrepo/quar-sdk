from frontend.quar.ast_nodes import (
    Integer,
    Double,
    Variable,
    BinaryOperation,
    VariableDeclaration,
    Assignment,
    FunctionCall,
)

class CCodeGenerator:

    def __init__(self):
        self.variable_types = {}

    def generate(self, program, variable_types=None):
        self.variable_types = variable_types or {}
        lines = [
            "#include <stdio.h>",
            "",
            "int main(void) {",
        ]

        for statement in program:
            generated = self.generate_statement(statement)
            lines.append(f"    {generated}")

        lines.append("    return 0;")
        lines.append("}")

        return "\n".join(lines)
        # Return complete generated C source

    def generate_statement(self, statement):

        if isinstance(statement, VariableDeclaration):
            value = self.generate_expression(statement.value)

            c_type = self.get_c_type(
                statement.var_type
            )

            return (
                f"{c_type} {statement.name} = {value};"
            )

        if isinstance(statement, Assignment):
            value = self.generate_expression(statement.value)

            if statement.name in self.variable_types:
                c_type = self.get_c_type(
                    self.variable_types[statement.name]
                )

                return (
                    f"{c_type} {statement.name} = {value};"
                )

            return (
                f"{statement.name} = {value};"
            )

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

        if isinstance(expression, Double):
            return repr(expression.value)
            # Convert double node to C text

        if isinstance(expression, Variable):
            return expression.name
            # Return C variable name

        if isinstance(expression, BinaryOperation):
            left = self.generate_expression(
                expression.left
            )

            right = self.generate_expression(
                expression.right
            )

            return (
                f"({left} {expression.operator} {right})"
            )
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
        if quar_type == "int":
            return "int"
        if quar_type == "double":
            return "double"

        raise ValueError(
            f"Unsupported Quar type: '{quar_type}'"
        )

    def infer_expression_type(self, expression):
        if isinstance(expression, Integer):
            return "int"

        if isinstance(expression, Double):
            return "double"

        if isinstance(expression, Variable):
            return self.variable_types.get(
                expression.name,
                "int"
            )

        if isinstance(expression, BinaryOperation):
            left_type = self.infer_expression_type(
                expression.left
            )
            right_type = self.infer_expression_type(
                expression.right
            )

            if "double" in (
                left_type,
                right_type,
            ):
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

            if argument_type == "double":
                result = (
                    f'printf("%g\\n", {arguments[0]})'
                )
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
                f"{call.name}({', '.join(arguments)})"
            )

        if statement_mode:
            return result + ";"

        return result
        # Return generated C function call