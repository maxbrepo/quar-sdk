"""Conservative numeric conversion checks using the canonical Quar type table."""

from frontend.quar.numeric_types import (
    canonical_numeric_type, integer_range, is_integer_type, is_float_type,
    integer_conversion_is_safe,
)
from qrvm.inspector_diagnostics import AnalysisStatus, Diagnostic, InspectionResult, Severity


def inspect_numeric_conversion(source_type: str, target_type: str, *, literal: int | None = None) -> InspectionResult:
    """Classify a numeric conversion; return diagnostics without changing compiler behavior."""
    source = canonical_numeric_type(source_type)
    target = canonical_numeric_type(target_type)
    if not (is_integer_type(source) or is_float_type(source)):
        return InspectionResult(AnalysisStatus.UNSUPPORTED)
    if not (is_integer_type(target) or is_float_type(target)):
        return InspectionResult(AnalysisStatus.UNSUPPORTED)

    # An integer literal is evidence only when the source is an integer type.
    # A floating-point conversion cannot be proven safe by an integer hint.
    if literal is not None and not isinstance(literal, int):
        raise TypeError("literal must be an integer or None")
    if literal is not None and is_integer_type(source):
        source_low, source_high = integer_range(source)
        if not source_low <= literal <= source_high:
            return InspectionResult(AnalysisStatus.FAIL, (Diagnostic(
                "QI-NUM-005", Severity.ERROR,
                f"Constant {literal} is outside the source range of {source} ({source_low}..{source_high})",
                "numeric-conversion",
            ),))

    if literal is not None and is_integer_type(source) and is_integer_type(target):
        low, high = integer_range(target)
        if not low <= literal <= high:
            return InspectionResult(AnalysisStatus.FAIL, (Diagnostic(
                "QI-NUM-001", Severity.ERROR,
                f"Constant {literal} is outside the range of {target} ({low}..{high})",
                "numeric-conversion",
            ),))

    if source == target:
        return InspectionResult(AnalysisStatus.PASS)
    if is_integer_type(source) and is_integer_type(target):
        if integer_conversion_is_safe(source, target):
            return InspectionResult(AnalysisStatus.PASS)
        if literal is not None:
            return InspectionResult(AnalysisStatus.PASS)
        return InspectionResult(AnalysisStatus.UNKNOWN, (Diagnostic(
            "QI-NUM-002", Severity.WARNING,
            f"Conversion from {source} to {target} may narrow the value range",
            "numeric-conversion",
        ),))
    if is_float_type(source) and is_integer_type(target):
        return InspectionResult(AnalysisStatus.UNKNOWN, (Diagnostic(
            "QI-NUM-003", Severity.WARNING,
            f"Conversion from {source} to {target} may truncate or overflow",
            "numeric-conversion",
        ),))
    if is_integer_type(source) and is_float_type(target):
        return InspectionResult(AnalysisStatus.UNKNOWN, (Diagnostic(
            "QI-NUM-004", Severity.WARNING,
            f"Conversion from {source} to {target} may lose integer precision",
            "numeric-conversion",
        ),))
    # Floating-point range and precision rules require target-specific semantics.
    return InspectionResult(AnalysisStatus.UNKNOWN)
