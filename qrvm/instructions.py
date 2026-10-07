from enum import Enum, auto


class OpCode(Enum):
    PUSH_INT = auto()
    PUSH_DOUBLE = auto()
    PUSH_BOOL = auto()
    PUSH_CHAR = auto()
    PUSH_STRING = auto()

    LOAD = auto()
    STORE = auto()
    POP = auto()

    ARRAY_NEW = auto()
    ARRAY_LOAD = auto()
    ARRAY_STORE = auto()
    LENGTH = auto()
    STRING_OP = auto()

    OBJECT_NEW = auto()
    MEMBER_LOAD = auto()
    MEMBER_STORE = auto()
    TUPLE_NEW = auto()
    TUPLE_UNPACK = auto()
    VARIANT_NEW = auto()
    MATCH_VARIANT = auto()

    ADD = auto()
    SUB = auto()
    MUL = auto()
    DIV = auto()
    MOD = auto()
    BIT_AND = auto()
    BIT_OR = auto()
    BIT_XOR = auto()
    BIT_NOT = auto()
    SHIFT_LEFT = auto()
    SHIFT_RIGHT = auto()

    EQUAL = auto()
    NOT_EQUAL = auto()
    LESS = auto()
    LESS_EQUAL = auto()
    GREATER = auto()
    GREATER_EQUAL = auto()

    LOGICAL_AND = auto()
    LOGICAL_OR = auto()
    LOGICAL_NOT = auto()
    NEGATE = auto()

    JUMP_IF_FALSE = auto()
    JUMP = auto()

    PRINT = auto()

    CALL = auto()
    RETURN = auto()

    HALT = auto()