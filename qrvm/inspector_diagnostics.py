"""Canonical diagnostic records for Quar Inspector.

This module stores findings; it does not claim to prove program safety.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Severity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    HINT = "HINT"


class AnalysisStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True)
class SourceLocation:
    path: str
    line: int
    column: int

    def __post_init__(self) -> None:
        if self.line < 1 or self.column < 1:
            raise ValueError("Source locations are one-based positive integers")


@dataclass(frozen=True)
class SourceRange:
    """Half-open source span: start included, end excluded.

    Both endpoints refer to the same file and use one-based coordinates.
    """
    start: SourceLocation
    end: SourceLocation

    def __post_init__(self) -> None:
        if self.start.path != self.end.path:
            raise ValueError("Source range endpoints must belong to the same file")
        if (self.end.line, self.end.column) <= (self.start.line, self.start.column):
            raise ValueError("Source range end must follow its start")


@dataclass(frozen=True)
class Diagnostic:
    code: str
    severity: Severity
    message: str
    origin: str
    location: Optional[SourceLocation] = None
    suggestion: Optional[str] = None
    source_range: Optional[SourceRange] = None

    def __post_init__(self) -> None:
        if not self.code or not self.message or not self.origin:
            raise ValueError("Diagnostic code, message and origin are required")
        if self.source_range is not None and self.location is not None:
            if self.source_range.start != self.location:
                raise ValueError("Diagnostic location must equal source range start")


@dataclass(frozen=True)
class InspectionResult:
    status: AnalysisStatus
    diagnostics: tuple[Diagnostic, ...] = ()

    def __post_init__(self) -> None:
        if self.status == AnalysisStatus.PASS and any(
            item.severity == Severity.ERROR for item in self.diagnostics
        ):
            raise ValueError("A passing inspection cannot contain errors")

    @property
    def has_errors(self) -> bool:
        """Return whether this result contains a blocking error."""
        return any(item.severity == Severity.ERROR for item in self.diagnostics)
