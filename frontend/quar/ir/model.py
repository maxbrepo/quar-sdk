"""Backend-independent immutable Quar IR data model."""
from dataclasses import dataclass

@dataclass(frozen=True)
class IRFunction:
    symbol: str
    return_type: str
    parameters: tuple[tuple[str, str], ...]
    body: tuple[object, ...] = ()


@dataclass(frozen=True)
class IRFunctionDefinition:
    """Executable function with parameter defaults preserved as IR expressions."""
    name: str
    return_type: str
    parameters: tuple[tuple[str, str, object | None], ...]
    body: tuple[object, ...]


@dataclass(frozen=True)
class IRModule:
    module_id: str
    dependencies: tuple[str, ...]
    functions: tuple[IRFunction, ...]


@dataclass(frozen=True)
class IRProject:
    modules: tuple[IRModule, ...]
    entry_module: str | None = None
    entry_body: tuple[object, ...] = ()


@dataclass(frozen=True)
class IRLiteral:
    value: int | float

@dataclass(frozen=True)
class IRReference:
    name: str

@dataclass(frozen=True)
class IRBinary:
    operator: str
    left: object
    right: object

@dataclass(frozen=True)
class IRCall:
    symbol: str
    arguments: tuple[object, ...]

@dataclass(frozen=True)
class IRDeclare:
    name: str
    type_name: str
    value: object

@dataclass(frozen=True)
class IRAssign:
    name: str
    value: object

@dataclass(frozen=True)
class IRReturn:
    value: object

class UnsupportedIRNode(ValueError):
    pass



@dataclass(frozen=True)
class IRBoolean:
    value: bool

@dataclass(frozen=True)
class IRUnary:
    operator: str
    operand: object

@dataclass(frozen=True)
class IRIf:
    condition: object
    then_body: tuple[object, ...]
    else_body: tuple[object, ...]

@dataclass(frozen=True)
class IRWhile:
    condition: object
    body: tuple[object, ...]

@dataclass(frozen=True)
class IRFor:
    counter_name: str
    start: object
    comparison: IRBinary
    body: tuple[object, ...]
    step: int = 1
    direction: int = 0

@dataclass(frozen=True)
class IRLoop:
    body: tuple[object, ...]

@dataclass(frozen=True)
class IRDoWhile:
    body: tuple[object, ...]
    condition: object

@dataclass(frozen=True)
class IRBreak:
    pass

@dataclass(frozen=True)
class IRContinue:
    pass


@dataclass(frozen=True)
class IRArrayNew:
    element_type: str
    name: str
    size: int | None
    initial_values: tuple[object, ...] | None = None
    second_size: int | None = None
    dynamic: bool = False

@dataclass(frozen=True)
class IRArrayGet:
    name: str
    index: object
    second_index: object | None = None

@dataclass(frozen=True)
class IRArraySet:
    name: str
    index: object
    value: object
    second_index: object | None = None


@dataclass(frozen=True)
class IRTypeField:
    field_type: str
    name: str

@dataclass(frozen=True)
class IRStructDefinition:
    name: str
    fields: tuple[IRTypeField, ...]
    is_record: bool = False

@dataclass(frozen=True)
class IRObjectNew:
    type_name: str
    name: str
    arguments: tuple[object, ...]

@dataclass(frozen=True)
class IRMemberGet:
    object_name: str
    member_name: str

@dataclass(frozen=True)
class IRMemberSet:
    object_name: str
    member_name: str
    value: object


@dataclass(frozen=True)
class IRSwitchCase:
    value: object
    body: tuple[object, ...]

@dataclass(frozen=True)
class IRSwitch:
    expression: object
    cases: tuple[IRSwitchCase, ...]
    default_body: tuple[object, ...]

@dataclass(frozen=True)
class IRMatchArm:
    variant_name: str
    bindings: tuple[str, ...]
    body: tuple[object, ...]

@dataclass(frozen=True)
class IRMatch:
    expression: object
    arms: tuple[IRMatchArm, ...]
    default_body: tuple[object, ...]


@dataclass(frozen=True)
class IRString:
    value: str

@dataclass(frozen=True)
class IRThrow:
    message: object
    cause: object | None = None

@dataclass(frozen=True)
class IRTryCatch:
    try_body: tuple[object, ...]
    error_name: str
    catch_body: tuple[object, ...]


@dataclass(frozen=True)
class IRChar:
    value: str


@dataclass(frozen=True)
class IRConstant:
    name: str
    type_name: str | None
    value: object


@dataclass(frozen=True)
class IRTuple:
    values: tuple[object, ...]

@dataclass(frozen=True)
class IRTupleDeclare:
    name: str
    value: object

@dataclass(frozen=True)
class IRDestructure:
    bindings: tuple[tuple[str, str], ...]
    value: object

@dataclass(frozen=True)
class IRTypeAlias:
    name: str
    target_type: str


@dataclass(frozen=True)
class IREnumDefinition:
    name: str
    members: tuple[object, ...]

@dataclass(frozen=True)
class IREnumVariant:
    name: str
    payload_types: tuple[str, ...]

@dataclass(frozen=True)
class IRVariantNew:
    enum_name: str
    variant_name: str
    arguments: tuple[object, ...]

@dataclass(frozen=True)
class IRNamedArgument:
    name: str
    value: object

@dataclass(frozen=True)
class IRWithFile:
    path: object
    mode: object
    name: str
    body: tuple[object, ...]


@dataclass(frozen=True)
class IRClassField:
    type_name: str
    name: str
    visibility: str


@dataclass(frozen=True)
class IRClassParameter:
    type_name: str
    name: str
    default_value: object | None = None


@dataclass(frozen=True)
class IRClassConstructor:
    parameters: tuple[IRClassParameter, ...]
    body: tuple[object, ...]
    visibility: str


@dataclass(frozen=True)
class IRClassMethod:
    name: str
    return_type: str
    parameters: tuple[IRClassParameter, ...]
    body: tuple[object, ...]
    visibility: str


@dataclass(frozen=True)
class IRClassDefinition:
    name: str
    fields: tuple[IRClassField, ...]
    constructor: IRClassConstructor | None
    methods: tuple[IRClassMethod, ...]
