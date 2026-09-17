
# ============================================================
# LEXER
# ============================================================

from .tokens import Token, TokenType
from .errors import LexerError

class Lexer:

    def __init__(self, source):
        self.source = source

        self.pos = 0
        self.line = 1
        self.column = 1

    def current_char(self):
        if self.pos >= len(self.source):
            return None

        return self.source[self.pos]

    def advance(self):
        char = self.current_char()

        if char is None:
            return

        self.pos += 1

        if char == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1

    def skip_whitespace(self):
        while True:
            char = self.current_char()

            if char is None:
                return

            if char in " \t\r\n":
                self.advance()
            else:
                return

    def read_number(self):
        start_line = self.line
        start_column = self.column

        value = ""

        while True:
            char = self.current_char()

            if char is None or not char.isdigit():
                break

            value += char
            self.advance()

        return Token(
            TokenType.INTEGER,
            value,
            start_line,
            start_column
        )

    def read_identifier(self):
        start_line = self.line
        start_column = self.column

        value = ""

        while True:
            char = self.current_char()

            if char is None:
                break

            if char.isalnum() or char == "_":
                value += char
                self.advance()
            else:
                break

        # Keyword conosciute dal linguaggio
        keywords = {
            "int": TokenType.TYPE_INT,
        }

        token_type = keywords.get(
            value,
            TokenType.IDENTIFIER
        )

        return Token(
            token_type,
            value,
            start_line,
            start_column
        )

    def tokenize(self):

        tokens = []

        while True:

            self.skip_whitespace()

            char = self.current_char()

            if char is None:
                tokens.append(
                    Token(
                        TokenType.EOF,
                        "",
                        self.line,
                        self.column
                    )
                )

                return tokens

            line = self.line
            column = self.column

            # Numero
            if char.isdigit():
                tokens.append(self.read_number())
                continue

            # Identificatore / keyword
            if char.isalpha() or char == "_":
                tokens.append(self.read_identifier())
                continue

            # Operatori e simboli

            if char == "=":
                tokens.append(
                    Token(TokenType.ASSIGN, char, line, column)
                )

            elif char == "+":
                tokens.append(
                    Token(TokenType.PLUS, char, line, column)
                )

            elif char == "-":
                tokens.append(
                    Token(TokenType.MINUS, char, line, column)
                )

            elif char == "*":
                tokens.append(
                    Token(TokenType.MULTIPLY, char, line, column)
                )

            elif char == "/":
                tokens.append(
                    Token(TokenType.DIVIDE, char, line, column)
                )

            elif char == "(":
                tokens.append(
                    Token(TokenType.LEFT_PAREN, char, line, column)
                )

            elif char == ")":
                tokens.append(
                    Token(TokenType.RIGHT_PAREN, char, line, column)
                )

            elif char == ",":
                tokens.append(
                    Token(TokenType.COMMA, char, line, column)
                )

            elif char == ";":
                tokens.append(
                    Token(TokenType.END_STMT, char, line, column)
                )

            else:
                # FAIL FAST:
                # fermiamo immediatamente il lexer.
                raise LexerError(
                    f"Errore lessicale alla linea {line}, "
                    f"colonna {column}: carattere non valido '{char}'"
                )

            self.advance()
