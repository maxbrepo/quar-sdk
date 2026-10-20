"""Conservative static bounds inspection for Visual Quar arrays."""
from frontend.quar import ast_nodes as ast
from qrvm.inspector_diagnostics import AnalysisStatus, Diagnostic, InspectionResult, Severity
from qrvm.inspector_ast_locations import attach_node_location


def _constant_integer(expr):
    """Return a proven integer constant, or None when inference is inconclusive."""
    if isinstance(expr, ast.Integer):
        return expr.value
    if isinstance(expr, ast.UnaryOperation) and expr.operator in ('-', '+'):
        value = _constant_integer(expr.operand)
        return (-value if expr.operator == '-' else value) if value is not None else None
    if isinstance(expr, ast.BinaryOperation) and expr.operator in ('+', '-', '*'):
        left, right = _constant_integer(expr.left), _constant_integer(expr.right)
        if left is None or right is None:
            return None
        return {'+': lambda: left + right, '-': lambda: left - right, '*': lambda: left * right}[expr.operator]()
    return None


def inspect_array_bounds(statements, arrays=None, *, path=None):
    """Inspect supported AST nodes without claiming safety for unknown indices."""
    sizes = dict(arrays or {})
    diagnostics = []
    unknown = False
    unsupported = False

    def check_expr(expr):
        nonlocal unknown, unsupported
        if isinstance(expr, ast.ArrayAccess):
            check_access(expr.name, expr.index, expr.second_index)
        elif isinstance(expr, ast.BinaryOperation):
            check_expr(expr.left)
            check_expr(expr.right)
        elif isinstance(expr, ast.UnaryOperation):
            check_expr(expr.operand)
        elif isinstance(expr, ast.FunctionCall):
            for argument in expr.arguments:
                check_expr(argument)

    def check_access(name, first, second):
        nonlocal unknown, unsupported
        if name not in sizes:
            unsupported = True  # Symbol resolution belongs to Symbol Inspector.
            return
        dimensions = sizes[name]
        indices = (first,) if second is None else (first, second)
        if len(indices) != len(dimensions):
            unsupported = True  # Array rank errors belong to type checking.
            return
        for dimension, (index, size) in enumerate(zip(indices, dimensions), start=1):
            check_expr(index)
            value = _constant_integer(index)
            if value is None or size is None:
                unknown = True
            elif value < 0 or value >= size:
                finding = Diagnostic(
                    'QI-BND-001', Severity.ERROR,
                    f'Array {name} dimension {dimension}: index {value} is outside 0..{size - 1}',
                    'bounds-inspector',
                )
                diagnostics.append(attach_node_location(finding, index, path) if path else finding)

    for statement in statements:
        if isinstance(statement, ast.ArrayDeclaration):
            sizes[statement.name] = ((statement.size,) if statement.second_size is None
                                     else (statement.size, statement.second_size))
            for value in statement.initial_values or []:
                check_expr(value)
        elif isinstance(statement, ast.ArrayAssignment):
            check_access(statement.name, statement.index, statement.second_index)
            check_expr(statement.value)
        elif isinstance(statement, (ast.VariableDeclaration, ast.ConstantDeclaration, ast.Assignment, ast.ReturnStatement)):
            if statement.value is not None:
                check_expr(statement.value)
        elif isinstance(statement, ast.ArrayAccess):
            check_access(statement.name, statement.index, statement.second_index)
        else:
            unsupported = True
    status = (AnalysisStatus.FAIL if diagnostics else
              AnalysisStatus.UNSUPPORTED if unsupported else
              AnalysisStatus.UNKNOWN if unknown else AnalysisStatus.PASS)
    return InspectionResult(status, tuple(diagnostics))
