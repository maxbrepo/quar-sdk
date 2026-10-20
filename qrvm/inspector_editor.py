"""Toolkit-independent diagnostic transport for Quar Edit and other clients.

The compiler uses one-based, end-exclusive source coordinates. Editor ranges
are zero-based and end-exclusive, suitable for common text buffer APIs.
"""
from qrvm.inspector_format import pipeline_record


def _editor_point(point):
    """Convert a serialized source point to a zero-based editor point."""
    return {"line": point["line"] - 1, "character": point["column"] - 1}


def _editor_range(diagnostic):
    """Return a precise range, or None when no full source span is known."""
    source_range = diagnostic["range"]
    if source_range is None:
        return None
    start, end = source_range["start"], source_range["end"]
    if start["path"] != end["path"]:
        return None
    return {"start": _editor_point(start), "end": _editor_point(end)}


def editor_record(inspection):
    """Flatten an Inspector report into a JSON-compatible editor transport.

    Unknown coordinates are explicitly null; a single point is not fabricated
    into a character range. The original report/pass statuses are retained.
    """
    source = pipeline_record(inspection)
    findings = []
    for report in source["reports"]:
        for item in report["diagnostics"]:
            location = item["location"]
            findings.append({
                "scope": report["scope"],
                "code": item["code"],
                "severity": item["severity"],
                "message": item["message"],
                "origin": item["origin"],
                "suggestion": item["suggestion"],
                "path": None if location is None else location["path"],
                "position": None if location is None else _editor_point(location),
                "range": _editor_range(item),
            })
    return {
        "schema_version": 1,
        "coordinate_system": "zero_based_end_exclusive",
        "status": source["status"],
        "experimental": source["experimental"],
        "blocking": source["blocking"],
        "reports": [{"scope": report["scope"], "status": report["status"],
                     "passes": report["passes"]} for report in source["reports"]],
        "diagnostics": findings,
    }


def editor_json(inspection):
    """Serialize the editor transport without an editor or GUI dependency."""
    import json
    return json.dumps(editor_record(inspection), ensure_ascii=False, indent=2)
