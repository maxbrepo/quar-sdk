"""Conservative control-flow inspection for the supported Visual Quar AST subset.

This analysis does not infer loop termination or reference safety.
"""
from frontend.quar import ast_nodes as ast
from qrvm.inspector_diagnostics import AnalysisStatus, Diagnostic, InspectionResult, Severity
from qrvm.inspector_ast_locations import attach_node_location


class _Unsupported(Exception):
    pass


def inspect_control_flow(function, *, path=None):
    """Return diagnostics for reachability and missing returns in one function."""
    if not isinstance(function, ast.FunctionDefinition):
        raise TypeError('Expected FunctionDefinition')
    findings = []

    def emit(code, severity, message, node):
        diagnostic = Diagnostic(code, severity, message, "control_flow")
        findings.append(attach_node_location(diagnostic, node, path) if path else diagnostic)

    def condition(expression):
        if isinstance(expression, ast.Boolean):
            return expression.value
        if isinstance(expression, (ast.Variable, ast.Integer, ast.Double)):
            return None
        if isinstance(expression, ast.UnaryOperation):
            value = condition(expression.operand)
            if expression.operator in ('!', 'not') and value is not None:
                return not value
            return None
        if isinstance(expression, ast.BinaryOperation):
            return None
        raise _Unsupported(type(expression).__name__)

    def block(statements):
        guaranteed = False
        for statement in statements:
            if guaranteed:
                emit('QI-CFG-002', Severity.WARNING,
                     'Unreachable statement after guaranteed return', statement)
                continue
            if isinstance(statement, ast.ReturnStatement):
                guaranteed = True
            elif isinstance(statement, ast.IfStatement):
                constant = condition(statement.condition)
                if constant is not None:
                    emit('QI-CFG-003', Severity.HINT,
                         f'Condition is always {str(constant).lower()}', statement.condition)
                    guaranteed = block(statement.then_body if constant else statement.else_body)
                else:
                    then_returns = block(statement.then_body)
                    else_returns = block(statement.else_body)
                    guaranteed = then_returns and else_returns
            elif isinstance(statement, ast.WhileStatement):
                constant = condition(statement.condition)
                if constant is False:
                    emit('QI-CFG-003', Severity.HINT,
                         'Condition is always false', statement.condition)
                else:
                    block(statement.body)
                # Never assume a loop terminates or guarantees a return.
            elif isinstance(statement, (ast.VariableDeclaration, ast.ConstantDeclaration, ast.Assignment)):
                pass
            else:
                raise _Unsupported(type(statement).__name__)
        return guaranteed

    try:
        guaranteed = block(function.body)
    except _Unsupported as exc:
        emit('QI-CFG-900', Severity.INFO,
             f'Unsupported control-flow node: {exc}', function)
        return InspectionResult(AnalysisStatus.UNSUPPORTED, tuple(findings))
    if function.return_type not in ('void', 'none') and not guaranteed:
        emit('QI-CFG-001', Severity.ERROR,
             f'Function {function.name} may finish without returning a value', function)
    status = AnalysisStatus.FAIL if any(d.severity == Severity.ERROR for d in findings) else AnalysisStatus.PASS
    return InspectionResult(status, tuple(findings))
