"""Conservative constant-expression diagnostics for the Quar AST subset."""
from frontend.quar import ast_nodes as ast
from qrvm.inspector_diagnostics import AnalysisStatus, Diagnostic, InspectionResult, Severity


class _Unknown(Exception):
    """Indicate that an expression cannot be evaluated statically."""


def inspect_values(statements):
    """Inspect supported statements and return diagnostics without executing code."""
    diagnostics = []
    incomplete = False

    def evaluate(expr):
        nonlocal incomplete
        if isinstance(expr, (ast.Integer, ast.Double, ast.Boolean)):
            return expr.value
        if isinstance(expr, ast.Variable):
            raise _Unknown()
        if isinstance(expr, ast.UnaryOperation):
            value = evaluate(expr.operand)
            if expr.operator == '-' and type(value) in (int, float):
                return -value
            raise _Unknown()
        if isinstance(expr, ast.BinaryOperation):
            # Inspect both operands even if one cannot be evaluated.
            left_known = right_known = False
            try:
                left = evaluate(expr.left)
                left_known = True
            except _Unknown:
                pass
            try:
                right = evaluate(expr.right)
                right_known = True
            except _Unknown:
                pass
            if expr.operator in ('/', '//', '%') and right_known and type(right) in (int, float) and right == 0:
                diagnostics.append(Diagnostic('QI-VAL-001', Severity.ERROR,
                                              'Division or modulo by provable zero', 'values'))
                raise _Unknown()
            if not (left_known and right_known):
                raise _Unknown()
            if type(left) not in (int, float) or type(right) not in (int, float):
                raise _Unknown()
            if expr.operator == '+':
                return left + right
            if expr.operator == '-':
                return left - right
            if expr.operator == '*':
                return left * right
            # Do not infer division semantics without the language type rules.
            raise _Unknown()
        incomplete = True
        raise _Unknown()

    def expression(expr):
        try:
            evaluate(expr)
        except _Unknown:
            pass

    def walk(body):
        nonlocal incomplete
        for statement in body:
            if isinstance(statement, (ast.VariableDeclaration, ast.ConstantDeclaration)):
                if statement.value is not None:
                    expression(statement.value)
            elif isinstance(statement, ast.Assignment):
                expression(statement.value)
            elif isinstance(statement, ast.ReturnStatement):
                if statement.value is not None:
                    expression(statement.value)
            elif isinstance(statement, ast.IfStatement):
                expression(statement.condition)
                walk(statement.then_body)
                walk(statement.else_body)
            elif isinstance(statement, ast.WhileStatement):
                expression(statement.condition)
                walk(statement.body)
            else:
                incomplete = True
    walk(statements)
    if diagnostics:
        status = AnalysisStatus.FAIL
    elif incomplete:
        status = AnalysisStatus.UNSUPPORTED
    else:
        # A PASS means no demonstrated violation in the supported subset.
        status = AnalysisStatus.PASS
    return InspectionResult(status, tuple(diagnostics))
