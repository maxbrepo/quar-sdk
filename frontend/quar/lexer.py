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
            if char is None or char not in " \t\r\n":
                return
            self.advance()

    def read_number(self):
        start_line = self.line
        start_column = self.column
        value = ""
        has_decimal_point = False

        while True:
            char = self.current_char()
            if char is None:
                break
            if char.isdigit():
                value += char
                self.advance()
                continue
            if char == "." and not has_decimal_point:
                has_decimal_point = True
                value += char
                self.advance()
                continue
            break

        if value.endswith("."):
            raise LexerError(
                f"Lexical error at line {start_line}, "
                f"column {start_column}: invalid numeric literal '{value}'"
            )

        token_type = TokenType.DOUBLE if has_decimal_point else TokenType.INTEGER
        return Token(token_type, value, start_line, start_column)

    def read_identifier(self):
        start_line = self.line
        start_column = self.column
        value = ""

        while True:
            char = self.current_char()
            if char is None or not (char.isalnum() or char == "_"):
                break
            value += char
            self.advance()

        keywords = {
            "int": TokenType.TYPE_INT,
            "i8": TokenType.TYPE_I8,
            "i16": TokenType.TYPE_I16,
            "i32": TokenType.TYPE_I32,
            "i64": TokenType.TYPE_I64,
            "i128": TokenType.TYPE_I128,
            "u8": TokenType.TYPE_U8,
            "byte": TokenType.TYPE_BYTE,
            "u16": TokenType.TYPE_U16,
            "u32": TokenType.TYPE_U32,
            "u64": TokenType.TYPE_U64,
            "u128": TokenType.TYPE_U128,
            "f32": TokenType.TYPE_F32,
            "f64": TokenType.TYPE_F64,
            "float": TokenType.TYPE_F32,
            "const": TokenType.CONST,
            "double": TokenType.TYPE_DOUBLE,
            "bool": TokenType.TYPE_BOOL,
            "char": TokenType.TYPE_CHAR,
            "string": TokenType.TYPE_STRING,
            "bytes": TokenType.TYPE_BYTES,
            "short": TokenType.TYPE_SHORT,
            "ushort": TokenType.TYPE_USHORT,
            "uint": TokenType.TYPE_UINT,
            "long": TokenType.TYPE_LONG,
            "ulong": TokenType.TYPE_ULONG,
            "llong": TokenType.TYPE_LLONG,
            "ullong": TokenType.TYPE_ULLONG,
            "long_double": TokenType.TYPE_LONG_DOUBLE,
            "void": TokenType.TYPE_VOID,
            "true": TokenType.TRUE,
            "false": TokenType.FALSE,
            "and": TokenType.AND,
            "or": TokenType.OR,
            "not": TokenType.NOT,
            "if": TokenType.IF,
            "else": TokenType.ELSE,
            "while": TokenType.WHILE,
            "do": TokenType.DO,
            "for": TokenType.FOR,
            "loop": TokenType.LOOP,
            "class": TokenType.CLASS,
            "init": TokenType.INIT,
            "this": TokenType.THIS,
            "public": TokenType.PUBLIC,
            "private": TokenType.PRIVATE,
            "struct": TokenType.STRUCT,
            "enum": TokenType.ENUM,
            "record": TokenType.RECORD,
            "return": TokenType.RETURN,
            "alias": TokenType.ALIAS,
            "tuple": TokenType.TYPE_TUPLE,
            "import": TokenType.IMPORT,
            "as": TokenType.AS,
            "with": TokenType.WITH,
            "try": TokenType.TRY,
            "catch": TokenType.CATCH,
            "throw": TokenType.THROW,
            "from": TokenType.FROM,
            "switch": TokenType.SWITCH,
            "case": TokenType.CASE,
            "default": TokenType.DEFAULT,
            "match": TokenType.MATCH,
            "break": TokenType.BREAK,
            "continue": TokenType.CONTINUE,
        }

        return Token(
            keywords.get(value, TokenType.IDENTIFIER),
            value,
            start_line,
            start_column,
        )

    def tokenize(self):
        tokens = []

        while True:
            self.skip_whitespace()
            char = self.current_char()

            if char is None:
                tokens.append(Token(TokenType.EOF, "", self.line, self.column))
                return tokens

            line = self.line
            column = self.column

            if char == "'":
                self.advance()
                value = self.current_char()
                if value is None or value == "'":
                    raise LexerError(
                        f"Line {line}: invalid char literal"
                    )
                self.advance()
                if self.current_char() != "'":
                    raise LexerError(
                        f"Line {line}: char requires one character"
                    )
                self.advance()
                tokens.append(
                    Token(TokenType.CHAR, value, line, column)
                )
                continue

            if char == '"':
                self.advance()
                value = ""
                while (
                    self.current_char() is not None
                    and self.current_char() != '"'
                ):
                    if self.current_char() == "\\":
                        self.advance()
                        escaped = self.current_char()
                        escapes = {
                            "n": "\n",
                            "t": "\t",
                            "r": "\r",
                            '"': '"',
                            "\\": "\\",
                        }
                        if escaped not in escapes:
                            raise LexerError(
                                f"Line {line}: unsupported string escape"
                            )
                        value += escapes[escaped]
                        self.advance()
                        continue
                    value += self.current_char()
                    self.advance()
                if self.current_char() != '"':
                    raise LexerError(
                        f"Line {line}: unterminated string"
                    )
                self.advance()
                tokens.append(
                    Token(TokenType.STRING, value, line, column)
                )
                continue

            if char.isdigit():
                tokens.append(self.read_number())
                continue

            if char.isalpha() or char == "_":
                tokens.append(self.read_identifier())
                continue

            next_char = (
                self.source[self.pos + 1]
                if self.pos + 1 < len(self.source)
                else None
            )

            double_symbols = {
                "==": TokenType.EQUAL,
                "!=": TokenType.NOT_EQUAL,
                "<=": TokenType.LESS_EQUAL,
                ">=": TokenType.GREATER_EQUAL,
                "<<": TokenType.SHIFT_LEFT,
                ">>": TokenType.SHIFT_RIGHT,
                "+=": TokenType.PLUS_ASSIGN,
                "-=": TokenType.MINUS_ASSIGN,
                "*=": TokenType.MULTIPLY_ASSIGN,
                "/=": TokenType.DIVIDE_ASSIGN,
                "%=": TokenType.MODULO_ASSIGN,
            }

            pair = (
                char + next_char
                if next_char is not None
                else None
            )

            if pair in double_symbols:
                tokens.append(
                    Token(
                        double_symbols[pair],
                        pair,
                        line,
                        column,
                    )
                )
                self.advance()
                self.advance()
                continue

            symbols = {
                "=": TokenType.ASSIGN,
                "<": TokenType.LESS,
                ">": TokenType.GREATER,
                "+": TokenType.PLUS,
                "-": TokenType.MINUS,
                "*": TokenType.MULTIPLY,
                "/": TokenType.DIVIDE,
                "%": TokenType.MODULO,
                "&": TokenType.BIT_AND,
                "|": TokenType.BIT_OR,
                "^": TokenType.BIT_XOR,
                "~": TokenType.BIT_NOT,
                "(": TokenType.LEFT_PAREN,
                ")": TokenType.RIGHT_PAREN,
                "{": TokenType.LEFT_BRACE,
                "}": TokenType.RIGHT_BRACE,
                "[": TokenType.LEFT_BRACKET,
                "]": TokenType.RIGHT_BRACKET,
                ".": TokenType.DOT,
                ",": TokenType.COMMA,
                ";": TokenType.END_STMT,
                "?": TokenType.QUESTION,
            }

            token_type = symbols.get(char)
            if token_type is None:
                raise LexerError(
                    f"Lexical error at line {line}, "
                    f"column {column}: invalid character '{char}'"
                )

            tokens.append(Token(token_type, char, line, column))
            self.advance()
