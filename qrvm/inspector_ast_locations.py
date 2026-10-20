"""Conservative AST-to-diagnostic source location bridge.

Only consume positions explicitly supplied by the frontend. Never infer a
source span from node names or source-text searches: repeated tokens make that
ambiguous. Parser instrumentation can populate these attributes later.
"""
from dataclasses import replace
from typing import Any, Optional

from qrvm.inspector_diagnostics import Diagnostic, SourceLocation, SourceRange


def node_source_range(node: Any, path: str) -> Optional[SourceRange]:
    """Return an explicit, validated node span, or None if unavailable."""
    span = getattr(node, "source_range", None)
    if isinstance(span, SourceRange):
        return span if span.start.path == path else None
    start = getattr(node, "start", None)
    end = getattr(node, "end", None)
    if not (isinstance(start, tuple) and isinstance(end, tuple)
            and len(start) == 2 and len(end) == 2):
        return None
    if not all(type(value) is int for value in (*start, *end)):
        return None
    try:
        return SourceRange(SourceLocation(path, *start), SourceLocation(path, *end))
    except ValueError:
        return None


def node_source_location(node: Any, path: str) -> Optional[SourceLocation]:
    """Return the node's explicit starting location, if one exists."""
    span = node_source_range(node, path)
    if span is not None:
        return span.start
    line = getattr(node, "line", None)
    column = getattr(node, "column", None)
    if type(line) is not int or type(column) is not int:
        return None
    try:
        return SourceLocation(path, line, column)
    except ValueError:
        return None


def attach_node_location(diagnostic: Diagnostic, node: Any, path: str) -> Diagnostic:
    """Add explicit AST position metadata without overwriting existing data."""
    if diagnostic.location is not None or diagnostic.source_range is not None:
        return diagnostic
    span = node_source_range(node, path)
    if span is not None:
        return replace(diagnostic, location=span.start, source_range=span)
    location = node_source_location(node, path)
    return replace(diagnostic, location=location) if location is not None else diagnostic
