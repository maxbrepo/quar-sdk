from frontend.quar.ast_nodes import (
    Integer,
    Variable,
    BinaryOperation,
    VariableDeclaration,
    Assignment,
    FunctionCall,
)

from .instructions import OpCode


class QRVMCompiler:

    def compile(self, program):
        instructions = []

        for statement in program:
            instructions.extend(
                self.compile_statement(statement)
            )

        instructions.append(
            (OpCode.HALT, None)
        )

        return instructions
        # Return complete QRVM program

    def compile_statement(self, statement):
        instructions = []

        if isinstance(statement, VariableDeclaration):
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



            if statement.name == "sum":
                instructions.extend(
                    self.compile_expression(statement)
                )

            instructions.append(
                (OpCode.POP, None)
            )

            return instructions
            # Discard unused function result

        raise RuntimeError(
            f"Unsupported QRVM statement: "
            f"{type(statement).__name__}"
        )

    def compile_expression(self, expression):
        instructions = []

        if isinstance(expression, Integer):
            instructions.append(
                (OpCode.PUSH_INT, expression.value)
            )

            return instructions
            # Push integer onto stack

        if isinstance(expression, Variable):
            instructions.append(
                (OpCode.LOAD, expression.name)
            )

            return instructions
            # Load variable onto stack

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

        raise RuntimeError(
            f"Unsupported QRVM expression: "
            f"{type(expression).__name__}"
        )