"""Conservative AST adapter for numeric declaration and assignment inspection.

Only simple integer literals and variable-to-variable conversions are modeled.
Unsupported expressions remain explicitly inconclusive.
"""
from frontend.quar import ast_nodes as ast
from frontend.quar.numeric_types import canonical_numeric_type, is_integer_type, is_float_type
from qrvm.inspector_diagnostics import AnalysisStatus, Diagnostic, InspectionResult, Severity
from qrvm.inspector_numeric import inspect_numeric_conversion
from qrvm.inspector_ast_locations import attach_node_location


def _numeric(name: str) -> bool:
    canonical = canonical_numeric_type(name)
    return is_integer_type(canonical) or is_float_type(canonical)


def inspect_numeric_statements(statements, parameters=(), *, path=None) -> InspectionResult:
    """Inspect a linear AST sequence and return conversion diagnostics.

    Parameters may be FunctionParameter instances. Unsupported constructs are
    not silently treated as safe; this adapter never changes compilation.
    """
    types = {p.name: p.var_type for p in parameters}
    diagnostics = []
    inconclusive = False
    unsupported = False

    def located(diagnostic, node):
        """Preserve the finding and attach only verified AST coordinates."""
        return attach_node_location(diagnostic, node, path) if path is not None else diagnostic
    for statement in statements:
        if isinstance(statement, (ast.VariableDeclaration, ast.ConstantDeclaration)):
            target = statement.var_type
            value = statement.value
            if target is None:
                unsupported = True
                continue
            if statement.name in types:
                unsupported = True  # Duplicate declarations belong to Symbol Inspector.
            types[statement.name] = target
        elif isinstance(statement, ast.Assignment):
            target = types.get(statement.name)
            value = statement.value
            if target is None:
                unsupported = True  # Undeclared names belong to Symbol Inspector.
                continue
        else:
            unsupported = True
            continue
        if value is None:
            continue
        if not _numeric(target):
            continue
        if isinstance(value, ast.Integer):
            # Integer literals are mathematical integers, not implicitly i32.
            # Check representability directly in the destination type.
            canonical = canonical_numeric_type(target)
            if is_integer_type(canonical):
                from frontend.quar.numeric_types import integer_range
                low, high = integer_range(canonical)
                if not low <= value.value <= high:
                    diagnostics.append(located(Diagnostic(
                        'QI-NUM-001', Severity.ERROR,
                        f'Constant {value.value} is outside the range of {canonical} ({low}..{high})',
                        'numeric-ast',
                    ), value))
            else:
                inconclusive = True  # Floating-point exactness needs separate semantics.
        elif isinstance(value, ast.Variable):
            source = types.get(value.name)
            if source is None or not _numeric(source):
                unsupported = True
                continue
            result = inspect_numeric_conversion(source, target)
            diagnostics.extend(located(diagnostic, value) for diagnostic in result.diagnostics)
            inconclusive |= result.status == AnalysisStatus.UNKNOWN
            unsupported |= result.status == AnalysisStatus.UNSUPPORTED
        else:
            unsupported = True  # Never infer safety for unmodeled expressions.
    if any(item.severity == Severity.ERROR for item in diagnostics):
        status = AnalysisStatus.FAIL
    elif unsupported:
        status = AnalysisStatus.UNSUPPORTED
    elif inconclusive:
        status = AnalysisStatus.UNKNOWN
    else:
        status = AnalysisStatus.PASS
    return InspectionResult(status, tuple(diagnostics))
