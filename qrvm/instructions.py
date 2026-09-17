from enum import Enum, auto


class OpCode(Enum):
    PUSH_INT = auto()

    LOAD = auto()
    STORE = auto()
    POP = auto()

    ADD = auto()
    SUB = auto()
    MUL = auto()
    DIV = auto()

    PRINT = auto()

    HALT = auto()