"""AST-to-IR lowering. This is the only IR layer that imports AST nodes."""
from .model import (IRFunction, IRModule, IRProject, IRLiteral, IRReference, IRBinary, IRCall, IRDeclare, IRAssign, IRReturn, UnsupportedIRNode)
from ..ast_nodes import (ArrayDeclaration, ArrayAccess, ArrayAssignment, ForStatement, LoopStatement, DoWhileStatement, BreakStatement, ContinueStatement, FunctionDefinition, Integer, Double, Boolean, Variable, BinaryOperation, UnaryOperation, IfStatement, WhileStatement, VariableDeclaration, Assignment, FunctionCall, ReturnStatement)
from .model import IRTypeField, IRStructDefinition, IRObjectNew, IRMemberGet, IRMemberSet
from ..ast_nodes import TypeField, StructDefinition, RecordDefinition, ObjectDeclaration, MemberAccess, MemberAssignment
from .model import IRSwitchCase, IRSwitch, IRMatchArm, IRMatch
from ..ast_nodes import SwitchStatement, MatchStatement
from .model import IRString, IRThrow, IRTryCatch, IRChar, IRConstant
from ..ast_nodes import String, Char, ConstantDeclaration, ThrowStatement, TryCatchStatement
from .model import IRBoolean, IRUnary, IRIf, IRWhile, IRFor, IRLoop, IRDoWhile, IRBreak, IRContinue, IRArrayNew, IRArrayGet, IRArraySet

from .model import IRTuple, IRTupleDeclare, IRDestructure, IRTypeAlias
from ..ast_nodes import TupleLiteral, TupleDeclaration, DestructuringDeclaration, TypeAlias

from .model import IREnumDefinition, IREnumVariant, IRVariantNew, IRNamedArgument, IRWithFile
from ..ast_nodes import EnumDefinition, EnumVariant, VariantConstructor, NamedArgument, WithFileStatement

from .model import IRClassField, IRClassParameter, IRClassConstructor, IRClassMethod, IRClassDefinition
from ..ast_nodes import ClassDefinition


def _lower_class_parameter(parameter):
    return IRClassParameter(parameter.var_type, parameter.name,
                            lower_expression(parameter.default_value) if parameter.default_value is not None else None)


def lower_module_inventory(loader) -> IRProject:
    """Describe each physical module once, independent of C or VM backend.

    Only function signatures and dependency edges are represented so far.
    Bodies and executable operations require a later IR revision.
    """
    modules = []
    for record in loader.project_modules():
        functions = tuple(
            IRFunction(
                symbol=f"{record.path.relative_to(loader.project_root).as_posix()}::{node.name}",
                return_type=node.return_type,
                parameters=tuple((p.name, p.var_type) for p in node.parameters),

            )
            for node in record.statements if isinstance(node, FunctionDefinition)
        )
        modules.append(IRModule(
            module_id=record.path.relative_to(loader.project_root).as_posix(),
            dependencies=tuple(path.relative_to(loader.project_root).as_posix()
                               for path in record.dependencies),
            functions=functions,
        ))
    return IRProject(tuple(modules))

def lower_expression(node):
    """Lower a supported AST expression without retaining mutable AST nodes."""
    if isinstance(node, NamedArgument):
        return IRNamedArgument(node.name, lower_expression(node.value))
    if isinstance(node, VariantConstructor):
        return IRVariantNew(node.enum_name, node.variant_name, tuple(map(lower_expression, node.arguments)))
    if isinstance(node, TupleLiteral):
        return IRTuple(tuple(lower_expression(v) for v in node.values))
    if isinstance(node, (Integer, Double)):
        return IRLiteral(node.value)
    if isinstance(node, Char):
        return IRChar(node.value)
    if isinstance(node, String):
        return IRString(node.value)
    if isinstance(node, Boolean):
        return IRBoolean(node.value)
    if isinstance(node, UnaryOperation):
        return IRUnary(node.operator, lower_expression(node.operand))
    if isinstance(node, MemberAccess):
        return IRMemberGet(node.object_name, node.member_name)
    if isinstance(node, ArrayAccess):
        return IRArrayGet(node.name, lower_expression(node.index),
                          lower_expression(node.second_index) if node.second_index is not None else None)
    if isinstance(node, Variable):
        return IRReference(node.name)
    if isinstance(node, BinaryOperation):
        return IRBinary(node.operator, lower_expression(node.left),
                        lower_expression(node.right))
    if isinstance(node, FunctionCall):
        return IRCall(node.name, tuple(lower_expression(a) for a in node.arguments))
    raise UnsupportedIRNode(f"Unsupported expression: {type(node).__name__}")

def lower_statement(node):
    """Lower the supported executable subset; reject unsupported syntax explicitly."""
    if isinstance(node, FunctionDefinition):
        from .model import IRFunctionDefinition
        return IRFunctionDefinition(
            node.name, node.return_type,
            tuple((p.name, p.var_type,
                   lower_expression(p.default_value) if p.default_value is not None else None)
                  for p in node.parameters),
            tuple(map(lower_statement, node.body)))
    if isinstance(node, ClassDefinition):
        constructor = None
        if node.constructor is not None:
            constructor = IRClassConstructor(
                tuple(_lower_class_parameter(p) for p in node.constructor.parameters),
                tuple(map(lower_statement, node.constructor.body)), node.constructor.visibility)
        methods = tuple(IRClassMethod(
            method.function.name, method.function.return_type,
            tuple(_lower_class_parameter(p) for p in method.function.parameters),
            tuple(map(lower_statement, method.function.body)), method.visibility)
            for method in node.methods)
        return IRClassDefinition(node.name,
            tuple(IRClassField(f.field_type, f.name, f.visibility) for f in node.fields),
            constructor, methods)
    if isinstance(node, EnumDefinition):
        return IREnumDefinition(node.name, tuple(IREnumVariant(member.name, tuple(member.payload_types)) for member in node.members))
    if isinstance(node, WithFileStatement):
        return IRWithFile(lower_expression(node.path), lower_expression(node.mode), node.name, tuple(map(lower_statement, node.body)))
    if isinstance(node, TypeAlias):
        return IRTypeAlias(node.name, node.target_type)
    if isinstance(node, TupleDeclaration):
        return IRTupleDeclare(node.name, lower_expression(node.value))
    if isinstance(node, DestructuringDeclaration):
        return IRDestructure(tuple(tuple(pair) for pair in node.bindings), lower_expression(node.value))
    if isinstance(node, ConstantDeclaration):
        return IRConstant(node.name, node.var_type, lower_expression(node.value))
    if isinstance(node, ThrowStatement):
        return IRThrow(lower_expression(node.message), lower_expression(node.cause) if node.cause is not None else None)
    if isinstance(node, TryCatchStatement):
        return IRTryCatch(tuple(map(lower_statement, node.try_body)), node.error_name, tuple(map(lower_statement, node.catch_body)))
    if isinstance(node, SwitchStatement):
        return IRSwitch(lower_expression(node.expression),
            tuple(IRSwitchCase(lower_expression(case.value), tuple(map(lower_statement, case.body)))
                  for case in node.cases),
            tuple(map(lower_statement, node.default_body)))
    if isinstance(node, MatchStatement):
        return IRMatch(lower_expression(node.expression),
            tuple(IRMatchArm(arm.variant_name, tuple(arm.bindings),
                             tuple(map(lower_statement, arm.body))) for arm in node.arms),
            tuple(map(lower_statement, node.default_body)))
    if isinstance(node, (StructDefinition, RecordDefinition)):
        return IRStructDefinition(node.name, tuple(IRTypeField(f.field_type, f.name) for f in node.fields), isinstance(node, RecordDefinition))
    if isinstance(node, ObjectDeclaration):
        return IRObjectNew(node.type_name, node.name, tuple(lower_expression(a) for a in node.arguments))
    if isinstance(node, MemberAssignment):
        return IRMemberSet(node.object_name, node.member_name, lower_expression(node.value))
    if isinstance(node, ArrayDeclaration):
        return IRArrayNew(node.element_type, node.name, node.size,
                          tuple(lower_expression(x) for x in node.initial_values) if node.initial_values is not None else None,
                          node.second_size, node.dynamic)
    if isinstance(node, ArrayAssignment):
        return IRArraySet(node.name, lower_expression(node.index), lower_expression(node.value),
                          lower_expression(node.second_index) if node.second_index is not None else None)
    if isinstance(node, ForStatement):
        return IRFor(node.counter_name, lower_expression(node.start),
                     lower_expression(node.comparison),
                     tuple(map(lower_statement, node.body)), node.step, node.direction)
    if isinstance(node, LoopStatement):
        return IRLoop(tuple(map(lower_statement, node.body)))
    if isinstance(node, DoWhileStatement):
        return IRDoWhile(tuple(map(lower_statement, node.body)), lower_expression(node.condition))
    if isinstance(node, BreakStatement):
        return IRBreak()
    if isinstance(node, ContinueStatement):
        return IRContinue()
    if isinstance(node, IfStatement):
        return IRIf(lower_expression(node.condition), tuple(map(lower_statement, node.then_body)), tuple(map(lower_statement, node.else_body)))
    if isinstance(node, WhileStatement):
        return IRWhile(lower_expression(node.condition), tuple(map(lower_statement, node.body)))
    if isinstance(node, VariableDeclaration):
        return IRDeclare(node.name, node.var_type, lower_expression(node.value))
    if isinstance(node, Assignment):
        return IRAssign(node.name, lower_expression(node.value))
    if isinstance(node, ReturnStatement):
        return IRReturn(lower_expression(node.value) if node.value is not None else None)
    if isinstance(node, FunctionCall):
        return lower_expression(node)
    raise UnsupportedIRNode(f"Unsupported statement: {type(node).__name__}")

def lower_function_body(function):
    """Return immutable IR statements for a function's executable body."""
    return tuple(lower_statement(node) for node in function.body)

def lower_executable_project(loader) -> IRProject:
    """Lower the supported executable subset of all project functions."""
    inventory = lower_module_inventory(loader)
    records = loader.project_modules()
    modules = []
    for module, record in zip(inventory.modules, records):
        definitions = [n for n in record.statements if isinstance(n, FunctionDefinition)]
        functions = tuple(
            IRFunction(old.symbol, old.return_type, old.parameters,
                       lower_function_body(definition))
            for old, definition in zip(module.functions, definitions)
        )
        modules.append(IRModule(module.module_id, module.dependencies, functions))
    return IRProject(tuple(modules))


def lower_resolved_project(loader) -> IRProject:
    """Lower supported function bodies with alias-independent call identities."""
    from dataclasses import replace

    project = lower_executable_project(loader)
    records = loader.project_modules()
    modules = []
    for module, record in zip(project.modules, records):
        bindings = {alias: path.relative_to(loader.project_root).as_posix()
                    for alias, path in record.bindings}
        locals_ = set(record.symbols)

        def resolve(node):
            if isinstance(node, IRNamedArgument):
                return replace(node, value=resolve(node.value))
            if isinstance(node, IRVariantNew):
                arguments = tuple(map(resolve, node.arguments))
                # The parser represents a two-part qualified call as a variant.
                # Resolve it as an imported function only when the module loader
                # confirms both the alias and the exported symbol.
                target_module = bindings.get(node.enum_name)
                if target_module is not None:
                    target_record = next((item for item in records
                        if item.path.relative_to(loader.project_root).as_posix() == target_module), None)
                    if target_record is not None and node.variant_name in target_record.symbols:
                        return IRCall(f"{target_module}::{node.variant_name}", arguments)
                return replace(node, arguments=arguments)
            if isinstance(node, IRWithFile):
                return replace(node, path=resolve(node.path), mode=resolve(node.mode), body=tuple(map(resolve, node.body)))
            if isinstance(node, IRCall):
                name = node.symbol
                if name in locals_:
                    target = f"{module.module_id}::{name}"
                else:
                    target = None
                    for alias in sorted(bindings, key=len, reverse=True):
                        if name.startswith(alias + "."):
                            target = f"{bindings[alias]}::{name[len(alias) + 1:]}"
                            break
                    if target is None:
                        target = name
                return replace(node, symbol=target,
                               arguments=tuple(resolve(arg) for arg in node.arguments))
            if isinstance(node, IRBinary):
                return replace(node, left=resolve(node.left), right=resolve(node.right))
            if isinstance(node, IRTuple):
                return replace(node, values=tuple(map(resolve, node.values)))
            if isinstance(node, (IRTupleDeclare, IRDestructure)):
                return replace(node, value=resolve(node.value))
            if isinstance(node, IRUnary):
                return replace(node, operand=resolve(node.operand))
            if isinstance(node, IRThrow):
                return replace(node, message=resolve(node.message), cause=resolve(node.cause) if node.cause is not None else None)
            if isinstance(node, IRTryCatch):
                return replace(node, try_body=tuple(map(resolve, node.try_body)), catch_body=tuple(map(resolve, node.catch_body)))
            if isinstance(node, IRSwitch):
                return replace(node, expression=resolve(node.expression),
                    cases=tuple(replace(case, value=resolve(case.value),
                        body=tuple(map(resolve, case.body))) for case in node.cases),
                    default_body=tuple(map(resolve, node.default_body)))
            if isinstance(node, IRMatch):
                return replace(node, expression=resolve(node.expression),
                    arms=tuple(replace(arm, body=tuple(map(resolve, arm.body))) for arm in node.arms),
                    default_body=tuple(map(resolve, node.default_body)))
            if isinstance(node, IRIf):
                return replace(node, condition=resolve(node.condition), then_body=tuple(map(resolve, node.then_body)), else_body=tuple(map(resolve, node.else_body)))
            if isinstance(node, IRFor):
                return replace(node, start=resolve(node.start), comparison=resolve(node.comparison), body=tuple(map(resolve, node.body)))
            if isinstance(node, (IRLoop, IRDoWhile)):
                changes = {"body": tuple(map(resolve, node.body))}
                if isinstance(node, IRDoWhile):
                    changes["condition"] = resolve(node.condition)
                return replace(node, **changes)
            if isinstance(node, IRWhile):
                return replace(node, condition=resolve(node.condition), body=tuple(map(resolve, node.body)))
            if isinstance(node, (IRReturn, IRDeclare, IRAssign, IRConstant)):
                return replace(node, value=resolve(node.value))
            return node

        modules.append(replace(module, functions=tuple(
            replace(function, body=tuple(resolve(item) for item in function.body))
            for function in module.functions)))
    return IRProject(tuple(modules))


def lower_program_project(loader, entry_path) -> IRProject:
    """Lower module functions and supported entry-module statements to IR."""
    from pathlib import Path
    from dataclasses import replace
    from ..ast_nodes import ImportStatement

    project = lower_resolved_project(loader)
    entry = Path(entry_path).resolve().relative_to(loader.project_root).as_posix()
    record = next((r for r in loader.project_modules()
                   if r.path.relative_to(loader.project_root).as_posix() == entry), None)
    if record is None:
        raise ValueError(f"Entry module not loaded: {entry}")
    statements = tuple(lower_statement(node) for node in record.statements
                       if not isinstance(node, (ImportStatement, FunctionDefinition)))
    bindings = {alias: path.relative_to(loader.project_root).as_posix()
                for alias, path in record.bindings}
    local_functions = set(record.symbols)

    def resolve(node):
        if isinstance(node, IRVariantNew):
            arguments = tuple(map(resolve, node.arguments))
            target_module = bindings.get(node.enum_name)
            if target_module is not None:
                target_record = next((item for item in loader.project_modules()
                    if item.path.relative_to(loader.project_root).as_posix() == target_module), None)
                if target_record is not None and node.variant_name in target_record.symbols:
                    return IRCall(f"{target_module}::{node.variant_name}", arguments)
            return replace(node, arguments=arguments)
        if isinstance(node, IRCall):
            name = node.symbol
            if name in local_functions:
                name = f"{entry}::{name}"
            else:
                for alias in sorted(bindings, key=len, reverse=True):
                    if name.startswith(alias + "."):
                        name = f"{bindings[alias]}::{name[len(alias) + 1:]}"
                        break
            return replace(node, symbol=name,
                           arguments=tuple(resolve(a) for a in node.arguments))
        if isinstance(node, IRBinary):
            return replace(node, left=resolve(node.left), right=resolve(node.right))
        if isinstance(node, IRTuple):
            return replace(node, values=tuple(map(resolve, node.values)))
        if isinstance(node, (IRTupleDeclare, IRDestructure)):
            return replace(node, value=resolve(node.value))
        if isinstance(node, (IRReturn, IRDeclare, IRAssign, IRConstant)):
            return replace(node, value=resolve(node.value))
        return node

    return replace(project, entry_module=entry,
                   entry_body=tuple(resolve(node) for node in statements))
