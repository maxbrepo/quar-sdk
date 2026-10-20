"""Conservative symbol checks for straight-line Quar AST statements.

Control-flow constructs are deliberately unsupported until scoped analysis exists.
"""
from frontend.quar import ast_nodes as ast
from qrvm.inspector_diagnostics import AnalysisStatus, Diagnostic, InspectionResult, Severity


class UnsupportedSymbolNode(Exception):
    """Indicate that the inspected AST subset cannot establish symbol safety."""


def _reads(expr):
    """Return referenced variable names, rejecting expressions not yet modeled."""
    if isinstance(expr, ast.Variable):
        return (expr.name,)
    if isinstance(expr, (ast.Integer, ast.Double, ast.Boolean, ast.String, ast.Char)):
        return ()
    if isinstance(expr, ast.BinaryOperation):
        return _reads(expr.left) + _reads(expr.right)
    if isinstance(expr, ast.UnaryOperation):
        return _reads(expr.operand)
    raise UnsupportedSymbolNode(type(expr).__name__)


def inspect_symbols(statements, parameters=()):
    """Inspect a linear statement sequence; return canonical diagnostics.

    Parameters are names declared by the caller. A failing or unsupported
    result must not be interpreted as proof of overall program safety.
    """
    declared = set(parameters)
    used = set()
    findings = []
    try:
        for statement in statements:
            if isinstance(statement, (ast.VariableDeclaration, ast.ConstantDeclaration)):
                names = _reads(statement.value) if statement.value is not None else ()
                for name in names:
                    if name not in declared:
                        findings.append(Diagnostic('QI-SYM-001', Severity.ERROR, f'Undeclared variable: {name}', 'symbols'))
                    used.add(name)
                if statement.name in declared:
                    findings.append(Diagnostic('QI-SYM-002', Severity.ERROR, f'Duplicate declaration: {statement.name}', 'symbols'))
                declared.add(statement.name)
            elif isinstance(statement, ast.Assignment):
                for name in _reads(statement.value):
                    if name not in declared:
                        findings.append(Diagnostic('QI-SYM-001', Severity.ERROR, f'Undeclared variable: {name}', 'symbols'))
                    used.add(name)
                if statement.name not in declared:
                    findings.append(Diagnostic('QI-SYM-001', Severity.ERROR, f'Undeclared variable: {statement.name}', 'symbols'))
            elif isinstance(statement, ast.ReturnStatement):
                for name in _reads(statement.value) if statement.value is not None else ():
                    if name not in declared:
                        findings.append(Diagnostic('QI-SYM-001', Severity.ERROR, f'Undeclared variable: {name}', 'symbols'))
                    used.add(name)
            else:
                raise UnsupportedSymbolNode(type(statement).__name__)
    except UnsupportedSymbolNode as exc:
        findings.append(Diagnostic('QI-SYM-900', Severity.INFO, f'Unsupported symbol analysis node: {exc}', 'symbols'))
        return InspectionResult(AnalysisStatus.UNSUPPORTED, tuple(findings))
    for name in sorted(declared - used - set(parameters)):
        findings.append(Diagnostic('QI-SYM-003', Severity.HINT, f'Unused variable: {name}', 'symbols'))
    return InspectionResult(AnalysisStatus.FAIL if any(f.severity == Severity.ERROR for f in findings) else AnalysisStatus.PASS, tuple(findings))
