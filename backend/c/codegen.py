from frontend.quar.ast_nodes import (
    Integer,
    Variable,
    BinaryOperation,
    VariableDeclaration,
    Assignment,
    FunctionCall,
)

class CCodeGenerator:

    def generate(self, program):
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

            return (
                f"int {statement.name} = {value};"
            )

        if isinstance(statement, Assignment):
            value = self.generate_expression(statement.value)

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