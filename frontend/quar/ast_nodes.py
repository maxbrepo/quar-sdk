from dataclasses import dataclass


@dataclass
class Integer:
    value: int


@dataclass
class Double:
    value: float


@dataclass
class Boolean:
    value: bool


@dataclass
class Variable:
    name: str


@dataclass
class BinaryOperation:
    left: object
    operator: str
    right: object


@dataclass
class UnaryOperation:
    operator: str
    operand: object


@dataclass
class VariableDeclaration:
    var_type: str
    name: str
    value: object


@dataclass
class ConstantDeclaration:
    var_type: str | None
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


@dataclass
class NamedArgument:
    name: str
    value: object



@dataclass
class ImportStatement:
    module_path: str
    alias: str | None


@dataclass
class FunctionParameter:
    var_type: str
    name: str
    default_value: object | None = None


@dataclass
class ReturnStatement:
    value: object


@dataclass
class FunctionDefinition:
    return_type: str
    name: str
    parameters: list
    body: list



@dataclass
class IfStatement:
    condition: object
    then_body: list
    else_body: list


@dataclass
class WhileStatement:
    condition: object
    body: list


@dataclass
class ForStatement:
    counter_name: str
    start: object
    comparison: BinaryOperation
    body: list
    step: int = 1
    direction: int = 0


@dataclass
class LoopStatement:
    body: list


@dataclass
class ArrayDeclaration:
    element_type: str
    name: str
    size: int | None
    initial_values: list = None
    second_size: int = None
    dynamic: bool = False


@dataclass
class ArrayAccess:
    name: str
    index: object
    second_index: object = None


@dataclass
class ArrayAssignment:
    name: str
    index: object
    value: object
    second_index: object = None

@dataclass
class Char:
    value: str


@dataclass
class String:
    value: str


@dataclass
class TypeField:
    field_type: str
    name: str


@dataclass
class StructDefinition:
    name: str
    fields: list


@dataclass
class RecordDefinition:
    name: str
    fields: list


@dataclass
class EnumDefinition:
    name: str
    members: list


@dataclass
class ObjectDeclaration:
    type_name: str
    name: str
    arguments: list


@dataclass
class MemberAccess:
    object_name: str
    member_name: str


@dataclass
class MemberAssignment:
    object_name: str
    member_name: str
    value: object

@dataclass
class DoWhileStatement:
    body: list
    condition: object


@dataclass
class BreakStatement:
    pass


@dataclass
class ContinueStatement:
    pass


@dataclass
class SwitchCase:
    value: object
    body: list


@dataclass
class SwitchStatement:
    expression: object
    cases: list
    default_body: list


@dataclass
class TypeAlias:
    name: str
    target_type: str

@dataclass
class TupleLiteral:
    values: list
@dataclass
class TupleDeclaration:
    name: str
    value: object
@dataclass
class DestructuringDeclaration:
    bindings: list
    value: object
@dataclass
class EnumVariant:
    name: str
    payload_types: list
@dataclass
class VariantConstructor:
    enum_name: str
    variant_name: str
    arguments: list
@dataclass
class MatchArm:
    variant_name: str
    bindings: list
    body: list
@dataclass
class MatchStatement:
    expression: object
    arms: list
    default_body: list
