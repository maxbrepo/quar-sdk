"""Typed failures for the experimental borrow checker."""
from qrvm.ownership_analysis import OwnershipError


class UnsupportedBorrowError(OwnershipError):
    """The current analysis cannot prove safety for this construct."""
