"""Opt-in diagnostic gate for the restricted source-level borrow checker.

A PASS covers only the subset currently modeled, not full memory safety.
"""
from dataclasses import dataclass
from enum import Enum

from frontend.quar.errors import LexerError, ParserError
from qrvm.borrow_source import analyze_borrow_source
from qrvm.ownership_analysis import OwnershipError
from qrvm.borrow_errors import UnsupportedBorrowError


class BorrowStatus(str, Enum):
    PASS = 'PASS'
    ERROR = 'ERROR'
    UNSUPPORTED = 'UNSUPPORTED'


@dataclass(frozen=True)
class BorrowDiagnostic:
    status: BorrowStatus
    message: str
    statements: int = 0
    code: str = ""




def check_borrow_source(source: str, *, max_facts: int = 1024, pure_calls=(), infer_local_calls: bool = False) -> BorrowDiagnostic:
    """Return a diagnostic without silently accepting unmodeled constructs.

    Source syntax errors remain ERROR. Unsupported analysis constructs are
    UNSUPPORTED. Internal unexpected exceptions deliberately propagate.
    """
    if not isinstance(source, str):
        raise TypeError('Quar source must be a string')
    try:
        result = analyze_borrow_source(source, max_facts=max_facts, pure_calls=pure_calls, infer_local_calls=infer_local_calls)
    except LexerError as exc:
        return BorrowDiagnostic(BorrowStatus.ERROR, str(exc), code='LEXER_ERROR')
    except ParserError as exc:
        return BorrowDiagnostic(BorrowStatus.ERROR, str(exc), code='PARSER_ERROR')
    except UnsupportedBorrowError as exc:
        return BorrowDiagnostic(BorrowStatus.UNSUPPORTED, str(exc), code='UNSUPPORTED_CONSTRUCT')
    except OwnershipError as exc:
        return BorrowDiagnostic(BorrowStatus.ERROR, str(exc), code='BORROW_ERROR')
    return BorrowDiagnostic(BorrowStatus.PASS, 'Supported borrow checks passed', len(result.statements), 'BORROW_PASS')


def require_borrow_source(source: str, *, max_facts: int = 1024, pure_calls=(), infer_local_calls: bool = False) -> BorrowDiagnostic:
    """Strict opt-in gate: reject both ERROR and UNSUPPORTED outcomes."""
    diagnostic = check_borrow_source(source, max_facts=max_facts, pure_calls=pure_calls, infer_local_calls=infer_local_calls)
    if diagnostic.status is not BorrowStatus.PASS:
        raise OwnershipError(f'{diagnostic.status.value}: {diagnostic.message}')
    return diagnostic
