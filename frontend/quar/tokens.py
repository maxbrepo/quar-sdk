from dataclasses import dataclass
from enum import Enum, auto


class TokenType(Enum):
    TYPE_INT = auto()

    IDENTIFIER = auto()
    INTEGER = auto()

    ASSIGN = auto()

    PLUS = auto()
    MINUS = auto()
    MULTIPLY = auto()
    DIVIDE = auto()

    LEFT_PAREN = auto()
    RIGHT_PAREN = auto()

    COMMA = auto()
    END_STMT = auto()

    EOF = auto()


@dataclass
class Token:
    type: TokenType
    value: str
    line: int
    column: int