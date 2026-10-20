"""Structured filesystem errors for the QRVM."""

from enum import Enum


class IOErrorKind(str, Enum):
    NOT_FOUND = "not_found"
    PERMISSION_DENIED = "permission_denied"
    ALREADY_EXISTS = "already_exists"
    NOT_A_DIRECTORY = "not_a_directory"
    IS_A_DIRECTORY = "is_a_directory"
    INVALID_DATA = "invalid_data"
    OTHER = "other"


class QuarIOError(RuntimeError):
    def __init__(self, operation: str, kind: IOErrorKind, message: str):
        self.operation = operation
        self.kind = kind
        super().__init__(f"I/O error in {operation} [{kind.value}]: {message}")


def classify_io_error(error: Exception) -> IOErrorKind:
    if isinstance(error, FileNotFoundError):
        return IOErrorKind.NOT_FOUND
    if isinstance(error, PermissionError):
        return IOErrorKind.PERMISSION_DENIED
    if isinstance(error, FileExistsError):
        return IOErrorKind.ALREADY_EXISTS
    if isinstance(error, NotADirectoryError):
        return IOErrorKind.NOT_A_DIRECTORY
    if isinstance(error, IsADirectoryError):
        return IOErrorKind.IS_A_DIRECTORY
    if isinstance(error, (UnicodeError, ValueError, IndexError)):
        return IOErrorKind.INVALID_DATA
    return IOErrorKind.OTHER
