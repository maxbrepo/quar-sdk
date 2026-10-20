"""Conservative lexical-scope symbol analysis for a supported Quar AST subset.

Unsupported nodes never produce a successful proof of completeness.
"""
from frontend.quar import ast_nodes as ast
from qrvm.inspector_diagnostics import AnalysisStatus, Diagnostic, InspectionResult, Severity
from qrvm.inspector_ast_locations import attach_node_location


class _Unsupported(Exception):
    pass


def inspect_scopes(statements, parameters=(), *, path=None):
    """Inspect lexical declarations and reads; return an InspectionResult.

    Nested branches and loop bodies have independent lexical scopes. This
    checker does not attempt definite-assignment or lifetime proofs.
    """
    scopes = [{name: -(index + 1) for index, name in enumerate(parameters)}]
    reads = set()
    declarations = []
    next_binding = 0
    findings = []

    def emit(code, severity, message, node=None):
        diagnostic = Diagnostic(code, severity, message, "symbols")
        if path is not None and node is not None:
            diagnostic = attach_node_location(diagnostic, node, path)
        findings.append(diagnostic)

    def resolve(name):
        for depth in range(len(scopes) - 1, -1, -1):
            if name in scopes[depth]:
                return scopes[depth][name]
        return None

    def read(expression):
        if isinstance(expression, ast.Variable):
            depth = resolve(expression.name)
            if depth is None:
                emit('QI-SYM-001', Severity.ERROR, f'Undeclared variable: {expression.name}', expression)
            else:
                reads.add(depth)
        elif isinstance(expression, (ast.Integer, ast.Double, ast.Boolean, ast.String, ast.Char)):
            return
        elif isinstance(expression, ast.BinaryOperation):
            read(expression.left)
            read(expression.right)
        elif isinstance(expression, ast.UnaryOperation):
            read(expression.operand)
        else:
            raise _Unsupported(type(expression).__name__)

    def block(body, nested=False):
        if nested:
            scopes.append({})
        nonlocal next_binding
        for statement in body:
            if isinstance(statement, (ast.VariableDeclaration, ast.ConstantDeclaration)):
                if statement.value is not None:
                    read(statement.value)
                if statement.name in scopes[-1]:
                    emit('QI-SYM-002', Severity.ERROR, f'Duplicate declaration: {statement.name}', statement)
                else:
                    next_binding += 1
                    scopes[-1][statement.name] = next_binding
                    declarations.append((next_binding, statement.name, statement))
            elif isinstance(statement, ast.Assignment):
                read(statement.value)
                if resolve(statement.name) is None:
                    emit('QI-SYM-001', Severity.ERROR, f'Undeclared variable: {statement.name}', statement)
            elif isinstance(statement, ast.ReturnStatement):
                if statement.value is not None:
                    read(statement.value)
            elif isinstance(statement, ast.IfStatement):
                read(statement.condition)
                block(statement.then_body, nested=True)
                block(statement.else_body, nested=True)
            elif isinstance(statement, ast.WhileStatement):
                read(statement.condition)
                block(statement.body, nested=True)
            else:
                raise _Unsupported(type(statement).__name__)
        if nested:
            scopes.pop()

    try:
        block(statements)
    except _Unsupported as exc:
        emit('QI-SYM-900', Severity.INFO, f'Unsupported symbol analysis node: {exc}')
        return InspectionResult(AnalysisStatus.UNSUPPORTED, tuple(findings))

    for binding, name, declaration in declarations:
        if binding not in reads:
            emit('QI-SYM-003', Severity.HINT, f'Unused variable: {name}', declaration)
    status = AnalysisStatus.FAIL if any(d.severity == Severity.ERROR for d in findings) else AnalysisStatus.PASS
    return InspectionResult(status, tuple(findings))
