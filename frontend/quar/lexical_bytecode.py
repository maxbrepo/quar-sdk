"""Opt-in lexical storage lowering for the QRVM statement subset.

The input AST is copied: source names remain available to diagnostics and C codegen.
Unsupported statements fail explicitly rather than silently producing incorrect bindings.
"""
from copy import deepcopy

from .ast_nodes import (
    Assignment, BinaryOperation, Boolean, Double, IfStatement, Integer,
    String, Char, UnaryOperation, Variable, VariableDeclaration, ConstantDeclaration, ForStatement, WhileStatement,
    FunctionDefinition, FunctionCall, ReturnStatement, NamedArgument,
    ArrayDeclaration, ArrayAccess, ArrayAssignment,
    ObjectDeclaration, MemberAccess, MemberAssignment, StructDefinition,
    DoWhileStatement, LoopStatement, BreakStatement, ContinueStatement,
    SwitchStatement, TypeAlias, ThrowStatement,
    TupleLiteral, TupleDeclaration, DestructuringDeclaration,
    VariantConstructor, MatchStatement, WithFileStatement, TryCatchStatement,
    ClassDefinition, EnumDefinition, RecordDefinition,
)
from .lexical_lowering import LexicalNamePlanner


class LexicalBytecodeLowerer:
    def __init__(self, *, allow_inference: bool = False):
        self.names = LexicalNamePlanner()
        self.allow_inference = allow_inference
        self.inferred_storage_names = set()
        self.type_names = set()

    def expression(self, node):
        if isinstance(node, Variable):
            node.name = self.names.read(node.name)
        elif isinstance(node, ArrayAccess):
            self.expression(node.index)
            if node.second_index is not None:
                self.expression(node.second_index)
            node.name = self.names.read(node.name)
        elif isinstance(node, MemberAccess):
            # Enum variants use a type-qualified name rather than a variable.
            # A lexical variable with the same spelling still takes priority.
            if (node.object_name not in self.type_names or
                    self.names.bindings.resolve(node.object_name) is not None):
                node.object_name = self.names.read(node.object_name)
        elif isinstance(node, TupleLiteral):
            for value in node.values:
                self.expression(value)
        elif isinstance(node, VariantConstructor):
            for argument in node.arguments:
                self.expression(argument)
        elif isinstance(node, BinaryOperation):
            self.expression(node.left)
            self.expression(node.right)
        elif isinstance(node, FunctionCall):
            for argument in node.arguments:
                self.expression(argument)
        elif isinstance(node, NamedArgument):
            self.expression(node.value)
        elif isinstance(node, UnaryOperation):
            self.expression(node.operand)
        elif isinstance(node, (Integer, Double, Boolean, String, Char)) or node is None:
            pass
        else:
            raise NotImplementedError(f"Lexical expression: {type(node).__name__}")

    def statements(self, statements, *, nested=False):
        if nested:
            self.names.enter()
        try:
            for statement in statements:
                if isinstance(statement, (VariableDeclaration, ConstantDeclaration)):
                    self.expression(statement.value)
                    statement.name = self.names.declare(statement.name).storage_name
                elif isinstance(statement, TupleDeclaration):
                    self.expression(statement.value)
                    statement.name = self.names.declare(statement.name).storage_name
                elif isinstance(statement, DestructuringDeclaration):
                    self.expression(statement.value)
                    # Parser bindings retain a (type, name) pair. Preserve the
                    # declared type and rename only the variable identity.
                    statement.bindings = [
                        (type_name, self.names.declare(name).storage_name)
                        for type_name, name in statement.bindings
                    ]
                elif isinstance(statement, MatchStatement):
                    self.expression(statement.expression)
                    for arm in statement.arms:
                        self.names.enter()
                        try:
                            arm.bindings = [
                                self.names.declare(name).storage_name for name in arm.bindings
                            ]
                            self.statements(arm.body)
                        finally:
                            self.names.leave()
                    self.statements(statement.default_body, nested=True)
                elif isinstance(statement, WithFileStatement):
                    self.expression(statement.path)
                    self.expression(statement.mode)
                    self.names.enter()
                    try:
                        statement.name = self.names.declare(statement.name).storage_name
                        self.statements(statement.body)
                    finally:
                        self.names.leave()
                elif isinstance(statement, TryCatchStatement):
                    self.statements(statement.try_body, nested=True)
                    self.names.enter()
                    try:
                        statement.error_name = self.names.declare(statement.error_name).storage_name
                        self.statements(statement.catch_body)
                    finally:
                        self.names.leave()
                elif isinstance(statement, ArrayDeclaration):
                    for value in statement.initial_values or []:
                        self.expression(value)
                    statement.name = self.names.declare(statement.name).storage_name
                elif isinstance(statement, (StructDefinition, RecordDefinition, EnumDefinition)):
                    # Type, variant, and field names are not variable bindings.
                    pass
                elif isinstance(statement, ClassDefinition):
                    # Preserve class metadata. Constructor/method bodies have
                    # their own receiver semantics, not ordinary block scope.
                    # Do not rename them until their namespace is modeled.
                    pass
                elif isinstance(statement, ObjectDeclaration):
                    for argument in statement.arguments:
                        self.expression(argument)
                    statement.name = self.names.declare(statement.name).storage_name
                elif isinstance(statement, MemberAssignment):
                    self.expression(statement.value)
                    statement.object_name = self.names.read(statement.object_name)
                elif isinstance(statement, ArrayAssignment):
                    self.expression(statement.index)
                    if statement.second_index is not None:
                        self.expression(statement.second_index)
                    self.expression(statement.value)
                    statement.name = self.names.read(statement.name)
                elif isinstance(statement, Assignment):
                    self.expression(statement.value)
                    resolution = self.names.assign(
                        statement.name, allow_inference=self.allow_inference
                    )
                    statement.name = resolution.storage_name
                    if resolution.introduced:
                        self.inferred_storage_names.add(resolution.storage_name)
                elif isinstance(statement, ForStatement):
                    # The counter is assigned, not declared by the for header.
                    # Resolve it before entering the loop-body scope.
                    self.expression(statement.start)
                    # The for header may introduce its integer counter in
                    # every profile, including typed. This is a documented
                    # exception to ordinary implicit assignment.
                    counter = self.names.assign(
                        statement.counter_name, allow_inference=True
                    )
                    statement.counter_name = counter.storage_name
                    if counter.introduced:
                        self.inferred_storage_names.add(counter.storage_name)
                    self.expression(statement.comparison)
                    self.statements(statement.body, nested=True)
                elif isinstance(statement, DoWhileStatement):
                    # The condition executes after the body; body declarations
                    # must not leak into the surrounding scope.
                    self.statements(statement.body, nested=True)
                    self.expression(statement.condition)
                elif isinstance(statement, LoopStatement):
                    self.statements(statement.body, nested=True)
                elif isinstance(statement, SwitchStatement):
                    self.expression(statement.expression)
                    for case in statement.cases:
                        self.expression(case.value)
                        self.statements(case.body, nested=True)
                    self.statements(statement.default_body, nested=True)
                elif isinstance(statement, (BreakStatement, ContinueStatement, TypeAlias)):
                    pass
                elif isinstance(statement, ThrowStatement):
                    self.expression(statement.message)
                    self.expression(statement.cause)
                elif isinstance(statement, WhileStatement):
                    self.expression(statement.condition)
                    self.statements(statement.body, nested=True)
                elif isinstance(statement, ReturnStatement):
                    self.expression(statement.value)
                elif isinstance(statement, FunctionCall):
                    self.expression(statement)
                elif isinstance(statement, FunctionDefinition):
                    with self.names.bindings.function_scoped():
                        for parameter in statement.parameters:
                            self.expression(parameter.default_value)
                            parameter.name = self.names.declare(parameter.name).storage_name
                        self.statements(statement.body)
                elif isinstance(statement, IfStatement):
                    self.expression(statement.condition)
                    self.statements(statement.then_body, nested=True)
                    self.statements(statement.else_body, nested=True)
                else:
                    raise NotImplementedError(f"Lexical statement: {type(statement).__name__}")
        finally:
            if nested:
                self.names.leave()

    def lower(self, program):
        copied = deepcopy(program)
        self.type_names = {
            statement.name for statement in copied
            if isinstance(statement, (EnumDefinition, StructDefinition, RecordDefinition, ClassDefinition))
        }
        self.statements(copied)
        return copied
