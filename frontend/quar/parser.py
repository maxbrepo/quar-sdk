from .tokens import TokenType
from .errors import ParserError

from .ast_nodes import (
    Integer,
    Variable,
    BinaryOperation,
    VariableDeclaration,
    Assignment,
    FunctionCall,
)

class Parser:

    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def current(self):
        return self.tokens[self.pos]
        # Return current token

    def advance(self):
        token = self.current()

        if token.type != TokenType.EOF:
            self.pos += 1

        return token
        # Return token and advance position

    def expect(self, token_type):
        token = self.current()

        if token.type != token_type:
            raise ParserError(
                f"Line {token.line}: "
                f"expected {token_type.name}, "
                f"found {token.type.name}"
            )

        return self.advance()
        # Validate and consume expected token

    def parse(self):
        statements = []

        while self.current().type != TokenType.EOF:
            statements.append(
                self.parse_statement()
            )

        return statements
        # Return complete parsed program

    def parse_statement(self):
        token = self.current()

        if token.type == TokenType.TYPE_INT:
            return self.parse_variable_declaration()

        if token.type == TokenType.IDENTIFIER:
            next_token = self.tokens[self.pos + 1]

            if next_token.type == TokenType.ASSIGN:
                return self.parse_assignment()

            if next_token.type == TokenType.LEFT_PAREN:
                call = self.parse_function_call()

                self.expect(TokenType.END_STMT)

                return call

        raise ParserError(
            f"Line {token.line}: "
            f"unrecognized statement"
        )

    def parse_variable_declaration(self):
        self.expect(TokenType.TYPE_INT)

        name = self.expect(
            TokenType.IDENTIFIER
        ).value

        self.expect(TokenType.ASSIGN)

        value = self.parse_expression()

        self.expect(TokenType.END_STMT)

        return VariableDeclaration(
            "int",
            name,
            value
        )
        # Return variable declaration node

    def parse_assignment(self):
        name = self.expect(
            TokenType.IDENTIFIER
        ).value

        self.expect(TokenType.ASSIGN)

        value = self.parse_expression()

        self.expect(TokenType.END_STMT)

        return Assignment(
            name,
            value
        )
        # Return variable assignment node

    def parse_expression(self):
        left = self.parse_term()

        while self.current().type in (
            TokenType.PLUS,
            TokenType.MINUS
        ):
            operator = self.advance().value

            right = self.parse_term()

            left = BinaryOperation(
                left,
                operator,
                right
            )

        return left
        # Return addition or subtraction expression

    def parse_term(self):
        left = self.parse_primary()

        while self.current().type in (
            TokenType.MULTIPLY,
            TokenType.DIVIDE
        ):
            operator = self.advance().value

            right = self.parse_primary()

            left = BinaryOperation(
                left,
                operator,
                right
            )

        return left
        # Return multiplication or division expression

    def parse_primary(self):
        token = self.current()

        if token.type == TokenType.INTEGER:
            self.advance()

            value = int(token.value)
            # Convert string to integer value

            return Integer(value)

        if token.type == TokenType.IDENTIFIER:
            next_token = self.tokens[self.pos + 1]

            if next_token.type == TokenType.LEFT_PAREN:
                return self.parse_function_call()

            self.advance()

            return Variable(
                token.value
            )
            # Return variable reference node

        if token.type == TokenType.LEFT_PAREN:
            self.advance()

            expression = self.parse_expression()

            self.expect(TokenType.RIGHT_PAREN)

            return expression
            # Return parenthesized expression

        raise ParserError(
            f"Line {token.line}: "
            f"invalid expression"
        )

    def parse_function_call(self):
        name = self.expect(
            TokenType.IDENTIFIER
        ).value

        self.expect(TokenType.LEFT_PAREN)

        arguments = []

        if self.current().type != TokenType.RIGHT_PAREN:
            arguments.append(
                self.parse_expression()
            )

            while self.current().type == TokenType.COMMA:
                self.advance()

                arguments.append(
                    self.parse_expression()
                )

        self.expect(TokenType.RIGHT_PAREN)

        return FunctionCall(
            name,
            arguments
        )
        # Return parsed function call