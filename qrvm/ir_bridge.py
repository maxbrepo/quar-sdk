"""Compatibility bridge from the supported Quar IR subset to the existing QRVM."""
from frontend.quar import ast_nodes as ast
from frontend.quar.ir.model import (IRLiteral, IRBoolean, IRReference, IRBinary, IRUnary, IRCall, IRDeclare, IRAssign, IRReturn, IRIf, IRWhile, IRFor, IRLoop, IRDoWhile, IRBreak, IRContinue, UnsupportedIRNode)
from frontend.quar.ir.model import IRTypeField, IRStructDefinition, IRObjectNew, IRMemberGet, IRMemberSet
from frontend.quar.ir.model import IRArrayNew, IRArrayGet, IRArraySet
from frontend.quar.ir.model import IRSwitch, IRSwitchCase, IRMatch, IRMatchArm
from frontend.quar.ir.model import IRString, IRThrow, IRTryCatch, IRChar, IRConstant
from frontend.quar.ir.model import IRTuple, IRTupleDeclare, IRDestructure, IRTypeAlias
from qrvm.compiler import QRVMCompiler

from frontend.quar.ir.model import IREnumDefinition, IREnumVariant, IRVariantNew, IRNamedArgument, IRWithFile

from frontend.quar.ir.model import IRClassDefinition

def to_ast(node):
    """Reconstruct an AST node for the existing bytecode compiler."""
    from frontend.quar.ir.model import IRFunctionDefinition
    if isinstance(node, IRFunctionDefinition):
        return ast.FunctionDefinition(
            node.return_type, node.name,
            [ast.FunctionParameter(type_name, name,
                 to_ast(default) if default is not None else None)
             for name, type_name, default in node.parameters],
            [to_ast(item) for item in node.body])
    if isinstance(node, IRClassDefinition):
        def parameter(p):
            return ast.FunctionParameter(p.type_name, p.name,
                to_ast(p.default_value) if p.default_value is not None else None)
        constructor = None
        if node.constructor is not None:
            c = node.constructor
            constructor = ast.ClassConstructor([parameter(p) for p in c.parameters],
                [to_ast(item) for item in c.body], c.visibility)
        methods = [ast.ClassMethod(
            ast.FunctionDefinition(m.return_type, m.name,
                [parameter(p) for p in m.parameters], [to_ast(item) for item in m.body]),
            m.visibility) for m in node.methods]
        return ast.ClassDefinition(node.name,
            [ast.ClassField(f.type_name, f.name, f.visibility) for f in node.fields],
            constructor, methods)
    if isinstance(node, IREnumDefinition):
        return ast.EnumDefinition(node.name, [ast.EnumVariant(m.name, list(m.payload_types)) for m in node.members])
    if isinstance(node, IRVariantNew):
        return ast.VariantConstructor(node.enum_name, node.variant_name, [to_ast(a) for a in node.arguments])
    if isinstance(node, IRNamedArgument):
        return ast.NamedArgument(node.name, to_ast(node.value))
    if isinstance(node, IRWithFile):
        return ast.WithFileStatement(to_ast(node.path), to_ast(node.mode), node.name, [to_ast(s) for s in node.body])
    if isinstance(node, IRTuple):
        return ast.TupleLiteral([to_ast(v) for v in node.values])
    if isinstance(node, IRTupleDeclare):
        return ast.TupleDeclaration(node.name, to_ast(node.value))
    if isinstance(node, IRDestructure):
        return ast.DestructuringDeclaration([tuple(pair) for pair in node.bindings], to_ast(node.value))
    if isinstance(node, IRTypeAlias):
        return ast.TypeAlias(node.name, node.target_type)
    if isinstance(node, IRChar):
        return ast.Char(node.value)
    if isinstance(node, IRConstant):
        return ast.ConstantDeclaration(node.type_name, node.name, to_ast(node.value))
    if isinstance(node, IRString):
        return ast.String(node.value)
    if isinstance(node, IRThrow):
        return ast.ThrowStatement(to_ast(node.message), to_ast(node.cause) if node.cause is not None else None)
    if isinstance(node, IRTryCatch):
        return ast.TryCatchStatement([to_ast(s) for s in node.try_body], node.error_name, [to_ast(s) for s in node.catch_body])
    if isinstance(node, IRSwitch):
        return ast.SwitchStatement(to_ast(node.expression),
            [ast.SwitchCase(to_ast(case.value), [to_ast(s) for s in case.body]) for case in node.cases],
            [to_ast(s) for s in node.default_body])
    if isinstance(node, IRMatch):
        return ast.MatchStatement(to_ast(node.expression),
            [ast.MatchArm(arm.variant_name, list(arm.bindings), [to_ast(s) for s in arm.body])
             for arm in node.arms], [to_ast(s) for s in node.default_body])
    if isinstance(node, IRStructDefinition):
        fields = [ast.TypeField(f.field_type, f.name) for f in node.fields]
        return ast.RecordDefinition(node.name, fields) if node.is_record else ast.StructDefinition(node.name, fields)
    if isinstance(node, IRObjectNew):
        return ast.ObjectDeclaration(node.type_name, node.name, [to_ast(a) for a in node.arguments])
    if isinstance(node, IRMemberGet):
        return ast.MemberAccess(node.object_name, node.member_name)
    if isinstance(node, IRMemberSet):
        return ast.MemberAssignment(node.object_name, node.member_name, to_ast(node.value))
    if isinstance(node, IRArrayNew):
        return ast.ArrayDeclaration(node.element_type, node.name, node.size,
            [to_ast(x) for x in node.initial_values] if node.initial_values is not None else None,
            node.second_size, node.dynamic)
    if isinstance(node, IRArrayGet):
        return ast.ArrayAccess(node.name, to_ast(node.index),
            to_ast(node.second_index) if node.second_index is not None else None)
    if isinstance(node, IRArraySet):
        return ast.ArrayAssignment(node.name, to_ast(node.index), to_ast(node.value),
            to_ast(node.second_index) if node.second_index is not None else None)
    if isinstance(node, IRBoolean):
        return ast.Boolean(node.value)
    if isinstance(node, IRLiteral):
        return ast.Integer(node.value) if isinstance(node.value, int) else ast.Double(node.value)
    if isinstance(node, IRReference):
        return ast.Variable(node.name)
    if isinstance(node, IRBinary):
        return ast.BinaryOperation(to_ast(node.left), node.operator, to_ast(node.right))
    if isinstance(node, IRUnary):
        return ast.UnaryOperation(node.operator, to_ast(node.operand))
    if isinstance(node, IRCall):
        return ast.FunctionCall(node.symbol, [to_ast(a) for a in node.arguments])
    if isinstance(node, IRDeclare):
        return ast.VariableDeclaration(node.type_name, node.name, to_ast(node.value))
    if isinstance(node, IRAssign):
        return ast.Assignment(node.name, to_ast(node.value))
    if isinstance(node, IRReturn):
        return ast.ReturnStatement(to_ast(node.value) if node.value is not None else None)
    if isinstance(node, IRIf):
        return ast.IfStatement(to_ast(node.condition), [to_ast(s) for s in node.then_body], [to_ast(s) for s in node.else_body])
    if isinstance(node, IRFor):
        return ast.ForStatement(node.counter_name, to_ast(node.start),
                                to_ast(node.comparison), [to_ast(s) for s in node.body],
                                node.step, node.direction)
    if isinstance(node, IRLoop):
        return ast.LoopStatement([to_ast(s) for s in node.body])
    if isinstance(node, IRDoWhile):
        return ast.DoWhileStatement([to_ast(s) for s in node.body], to_ast(node.condition))
    if isinstance(node, IRBreak):
        return ast.BreakStatement()
    if isinstance(node, IRContinue):
        return ast.ContinueStatement()
    if isinstance(node, IRWhile):
        return ast.WhileStatement(to_ast(node.condition), [to_ast(s) for s in node.body])
    raise UnsupportedIRNode(f"Unsupported IR node for QRVM: {type(node).__name__}")

def compile_ir_statements(statements):
    """Compile supported IR statements through the existing QRVM compiler."""
    return QRVMCompiler().compile([to_ast(item) for item in statements])
