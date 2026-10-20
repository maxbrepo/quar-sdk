"""Stable terminal and structured output for experimental Inspector findings."""
import json
from typing import Optional

from qrvm.inspector_diagnostics import Diagnostic, SourceLocation


def format_diagnostic(item: Diagnostic, *, scope: Optional[str] = None) -> str:
    """Return a single human-readable finding without modifying its severity."""
    location = item.location
    where = f" {location.path}:{location.line}:{location.column}" if location else ""
    prefix = f"[{scope}] " if scope else ""
    if item.source_range is not None:
        span = item.source_range
        where = (f" {span.start.path}:{span.start.line}:{span.start.column}"
                 f"-{span.end.line}:{span.end.column}")
    message = f"{prefix}{item.severity.value} {item.code}{where}: {item.message}"
    return message + (f" (suggestion: {item.suggestion})" if item.suggestion else "")


def diagnostic_record(item: Diagnostic, *, scope: Optional[str] = None) -> dict:
    """Return a JSON-compatible record; unknown positions remain null."""
    location = item.location or (item.source_range.start if item.source_range else None)
    return {
        "code": item.code,
        "severity": item.severity.value,
        "message": item.message,
        "origin": item.origin,
        "scope": scope,
        "location": None if location is None else {
            "path": location.path, "line": location.line, "column": location.column,
        },
        "suggestion": item.suggestion,
        "range": None if item.source_range is None else {
            "start": {"path": item.source_range.start.path,
                      "line": item.source_range.start.line,
                      "column": item.source_range.start.column},
            "end": {"path": item.source_range.end.path,
                    "line": item.source_range.end.line,
                    "column": item.source_range.end.column},
        },
    }


def pipeline_record(inspection) -> dict:
    """Return an editor-friendly report retaining each analysis status."""
    return {
        "schema_version": 1,
        "status": inspection.status.value,
        "experimental": True,
        "blocking": False,
        "reports": [
            {
                "scope": scope,
                "status": report.result.status.value,
                "diagnostics": [diagnostic_record(item, scope=scope) for item in report.result.diagnostics],
                "passes": [{"name": name, "status": result.status.value}
                           for name, result in report.passes],
            }
            for scope, report in inspection.reports
        ],
    }


def pipeline_json(inspection) -> str:
    """Serialize an inspection into stable UTF-8 JSON for external consumers."""
    return json.dumps(pipeline_record(inspection), ensure_ascii=False, indent=2)
