from .errors import SemanticError

from .ast_nodes import (
    Integer,
    Variable,
    BinaryOperation,
    VariableDeclaration,
    Assignment,
    FunctionCall,
)


class SemanticAnalyzer:

    def __init__(self):
        self.variables = {}

        self.functions = {
            "print": {
                "arguments": 1,
                "return_type": "void",
            },
            "sum": {
                "arguments": 2,
                "return_type": "int",
            },
        }

    def analyze(self, program):

        for statement in program:
            self.analyze_statement(statement)

        return program
        # Return validated program AST

    def analyze_statement(self, statement):

        if isinstance(statement, VariableDeclaration):
            self.analyze_variable_declaration(statement)
            return

        if isinstance(statement, Assignment):
            self.analyze_assignment(statement)
            return

        if isinstance(statement, FunctionCall):
            self.analyze_function_call(statement)
            return

        raise SemanticError(
            f"Unsupported statement: {type(statement).__name__}"
        )

    def analyze_variable_declaration(self, declaration):

        if declaration.name in self.variables:
            raise SemanticError(
                f"Variable '{declaration.name}' is already declared"
            )

        value_type = self.analyze_expression(
            declaration.value
        )

        if value_type != declaration.var_type:
            raise SemanticError(
                f"Cannot assign '{value_type}' "
                f"to '{declaration.var_type}'"
            )

        self.variables[declaration.name] = declaration.var_type
        # Store declared variable type

    def analyze_assignment(self, assignment):

        if assignment.name not in self.variables:
            raise SemanticError(
                f"Variable '{assignment.name}' is not declared"
            )

        variable_type = self.variables[
            assignment.name
        ]

        value_type = self.analyze_expression(
            assignment.value
        )

        if variable_type != value_type:
            raise SemanticError(
                f"Cannot assign '{value_type}' "
                f"to '{variable_type}'"
            )

    def analyze_expression(self, expression):

        if isinstance(expression, Integer):
            return "int"

        if isinstance(expression, Variable):

            if expression.name not in self.variables:
                raise SemanticError(
                    f"Variable '{expression.name}' is not declared"
                )

            return self.variables[
                expression.name
            ]

        if isinstance(expression, BinaryOperation):
            return self.analyze_binary_operation(
                expression
            )

        if isinstance(expression, FunctionCall):
            return self.analyze_function_call(
                expression
            )

        raise SemanticError(
            f"Unsupported expression: {type(expression).__name__}"
        )

    def analyze_binary_operation(self, expression):

        left_type = self.analyze_expression(
            expression.left
        )

        right_type = self.analyze_expression(
            expression.right
        )

        if left_type != "int":
            raise SemanticError(
                "Left operand must be int"
            )

        if right_type != "int":
            raise SemanticError(
                "Right operand must be int"
            )

        return "int"
        # Return binary expression type

    def analyze_function_call(self, call):

        if call.name not in self.functions:
            raise SemanticError(
                f"Unknown function '{call.name}'"
            )

        function = self.functions[
            call.name
        ]

        expected_arguments = function[
            "arguments"
        ]

        if len(call.arguments) != expected_arguments:
            raise SemanticError(
                f"Function '{call.name}' expects "
                f"{expected_arguments} arguments, "
                f"received {len(call.arguments)}"
            )

        for argument in call.arguments:
            self.analyze_expression(argument)

        return function["return_type"]
        # Return declared function result type