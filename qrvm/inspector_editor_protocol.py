"""Validation boundary for the experimental Quar Inspector editor protocol.

This module has no dependency on GTK, the compiler AST, or editor widgets.
It validates the version-one transport without manufacturing source positions.
"""
import json


_STATUSES = frozenset(("PASS", "FAIL", "UNKNOWN", "UNSUPPORTED"))
_SEVERITIES = frozenset(("ERROR", "WARNING", "INFO", "HINT"))


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _point(value, label):
    _require(isinstance(value, dict), f"{label} must be an object")
    _require(set(value) == {"line", "character"}, f"{label} has invalid fields")
    for field in ("line", "character"):
        number = value[field]
        _require(type(number) is int and number >= 0,
                 f"{label}.{field} must be a nonnegative integer")


def validate_editor_record(payload):
    """Validate a version-one editor record and return it unchanged.

    Raises ValueError for malformed or unsupported payloads. A missing source
    position is valid and must remain null, not a guessed text range.
    """
    _require(isinstance(payload, dict), "Editor payload must be an object")
    _require(type(payload.get("schema_version")) is int and payload["schema_version"] == 1,
             "Unsupported editor schema version")
    _require(payload.get("coordinate_system") == "zero_based_end_exclusive",
             "Unsupported coordinate system")
    _require(payload.get("status") in _STATUSES, "Invalid overall status")
    _require(type(payload.get("experimental")) is bool, "Invalid experimental flag")
    _require(type(payload.get("blocking")) is bool, "Invalid blocking flag")
    reports = payload.get("reports")
    findings = payload.get("diagnostics")
    _require(isinstance(reports, list), "Reports must be a list")
    _require(isinstance(findings, list), "Diagnostics must be a list")
    for index, report in enumerate(reports):
        label = f"reports[{index}]"
        _require(isinstance(report, dict), f"{label} must be an object")
        _require(isinstance(report.get("scope"), str), f"{label}.scope is invalid")
        _require(report.get("status") in _STATUSES, f"{label}.status is invalid")
        passes = report.get("passes")
        _require(isinstance(passes, list), f"{label}.passes must be a list")
        for item in passes:
            _require(isinstance(item, dict) and isinstance(item.get("name"), str)
                     and item.get("status") in _STATUSES, f"{label} contains an invalid pass")
    for index, item in enumerate(findings):
        label = f"diagnostics[{index}]"
        _require(isinstance(item, dict), f"{label} must be an object")
        for key in ("scope", "code", "message", "origin"):
            _require(isinstance(item.get(key), str) and bool(item[key]),
                     f"{label}.{key} is invalid")
        _require(item.get("severity") in _SEVERITIES, f"{label}.severity is invalid")
        suggestion = item.get("suggestion")
        _require(suggestion is None or isinstance(suggestion, str),
                 f"{label}.suggestion is invalid")
        path = item.get("path")
        position = item.get("position")
        span = item.get("range")
        _require(path is None or isinstance(path, str), f"{label}.path is invalid")
        if position is not None:
            _require(path is not None, f"{label}.position requires a path")
            _point(position, f"{label}.position")
        if span is not None:
            _require(path is not None, f"{label}.range requires a path")
            _require(isinstance(span, dict) and set(span) == {"start", "end"},
                     f"{label}.range is invalid")
            _point(span["start"], f"{label}.range.start")
            _point(span["end"], f"{label}.range.end")
            start = (span["start"]["line"], span["start"]["character"])
            end = (span["end"]["line"], span["end"]["character"])
            _require(start < end, f"{label}.range must be end-exclusive and nonempty")
            _require(position is not None and position == span["start"],
                     f"{label}.position must equal range start")
    return payload


def parse_editor_json(data):
    """Decode and validate editor JSON; return its JSON-compatible record."""
    try:
        payload = json.loads(data)
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid editor JSON") from exc
    return validate_editor_record(payload)
