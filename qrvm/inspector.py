"""Unified, opt-in entry point for experimental Quar Inspector passes.

This module does not change compiler acceptance or certify memory safety.
"""
from dataclasses import dataclass
from typing import Iterable, Optional

from qrvm.inspector_diagnostics import AnalysisStatus, Diagnostic, InspectionResult
from qrvm.inspector_scopes import inspect_scopes
from qrvm.inspector_control_flow import inspect_control_flow
from qrvm.inspector_values import inspect_values
from qrvm.inspector_numeric_ast import inspect_numeric_statements
from qrvm.inspector_bounds import inspect_array_bounds


PASS_NAMES = ('scopes', 'control_flow', 'values', 'numeric', 'bounds')


@dataclass(frozen=True)
class InspectorReport:
    result: InspectionResult
    passes: tuple[tuple[str, InspectionResult], ...]


def combine_inspections(results: Iterable[InspectionResult]) -> InspectionResult:
    """Merge results without allowing PASS to conceal incomplete analyses."""
    results = tuple(results)
    diagnostics: list[Diagnostic] = []
    seen = set()
    for result in results:
        for item in result.diagnostics:
            key = (item.code, item.severity, item.message, item.origin, item.location, item.suggestion)
            if key not in seen:
                seen.add(key)
                diagnostics.append(item)
    statuses = {result.status for result in results}
    if any(item.severity.value == 'ERROR' for item in diagnostics) or AnalysisStatus.FAIL in statuses:
        status = AnalysisStatus.FAIL
    elif AnalysisStatus.UNSUPPORTED in statuses:
        status = AnalysisStatus.UNSUPPORTED
    elif AnalysisStatus.UNKNOWN in statuses:
        status = AnalysisStatus.UNKNOWN
    else:
        status = AnalysisStatus.PASS
    return InspectionResult(status, tuple(diagnostics))


def inspect_program(statements, *, function=None, parameters=(), enabled: Optional[Iterable[str]]=None, path=None) -> InspectorReport:
    """Run selected independent analyses on an existing frontend AST.

    Return a combined report and individual pass results. Function analysis
    runs only when an explicit FunctionDefinition is supplied.
    """
    selected = tuple(PASS_NAMES if enabled is None else enabled)
    unknown = set(selected) - set(PASS_NAMES)
    if unknown:
        raise ValueError(f'Unknown Inspector passes: {", ".join(sorted(unknown))}')
    if len(selected) != len(set(selected)):
        raise ValueError('Duplicate Inspector pass names')
    operations = {
        'scopes': lambda: inspect_scopes(statements, parameters=parameters, path=path),
        'control_flow': lambda: inspect_control_flow(function, path=path) if function is not None else InspectionResult(AnalysisStatus.UNSUPPORTED),
        'values': lambda: inspect_values(statements),
        'numeric': lambda: inspect_numeric_statements(statements, parameters=parameters, path=path),
        'bounds': lambda: inspect_array_bounds(statements, path=path),
    }
    passes = tuple((name, operations[name]()) for name in selected)
    return InspectorReport(combine_inspections(result for _, result in passes), passes)
