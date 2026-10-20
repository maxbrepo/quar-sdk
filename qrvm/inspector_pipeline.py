"""Opt-in Inspector reporting for the validated Visual Quar AST.

Diagnostics are advisory in this experimental integration; compilation gates
remain the responsibility of the existing semantic and safety analyzers.
"""
from dataclasses import dataclass
from frontend.quar.ast_nodes import FunctionDefinition
from qrvm.inspector import inspect_program
from qrvm.inspector_diagnostics import AnalysisStatus
from qrvm.inspector_format import format_diagnostic


@dataclass(frozen=True)
class PipelineInspection:
    reports: tuple
    status: AnalysisStatus


def inspect_validated_program(program, *, path=None):
    """Inspect top-level statements and functions; return all pass reports."""
    functions = tuple(node for node in program if isinstance(node, FunctionDefinition))
    top_level = tuple(node for node in program if not isinstance(node, FunctionDefinition))
    reports = []
    if top_level:
        reports.append(("<module>", inspect_program(top_level, enabled=("scopes", "values", "numeric", "bounds"), path=path)))
    for function in functions:
        params = tuple(param.name for param in function.parameters)
        reports.append((function.name, inspect_program(function.body, function=function,
                       parameters=params, enabled=("scopes", "control_flow", "values", "numeric", "bounds"), path=path)))
    statuses = {report.result.status for _, report in reports}
    if AnalysisStatus.FAIL in statuses:
        status = AnalysisStatus.FAIL
    elif AnalysisStatus.UNSUPPORTED in statuses:
        status = AnalysisStatus.UNSUPPORTED
    elif AnalysisStatus.UNKNOWN in statuses:
        status = AnalysisStatus.UNKNOWN
    else:
        status = AnalysisStatus.PASS
    return PipelineInspection(tuple(reports), status)


def format_pipeline_inspection(inspection):
    """Return readable diagnostics, including incomplete analysis states."""
    lines = [f"Quar Inspector: {inspection.status.value} (experimental, non-blocking)"]
    for name, report in inspection.reports:
        lines.append(f"  {name}: {report.result.status.value}")
        for finding in report.result.diagnostics:
            lines.append("    " + format_diagnostic(finding))
    return "\n".join(lines)
