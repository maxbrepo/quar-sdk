from dataclasses import dataclass


@dataclass
class Integer:
    value: int


@dataclass
class Variable:
    name: str


@dataclass
class BinaryOperation:
    left: object
    operator: str
    right: object


@dataclass
class VariableDeclaration:
    var_type: str
    name: str
    value: object


@dataclass
class Assignment:
    name: str
    value: object


@dataclass
class FunctionCall:
    name: str
    arguments: list