"""Regression tests for typed borrow diagnostics."""
import unittest
from qrvm.borrow_gate import BorrowStatus, check_borrow_source, require_borrow_source
from qrvm.borrow_errors import UnsupportedBorrowError
from qrvm.ownership_analysis import OwnershipError


class BorrowDiagnosticTests(unittest.TestCase):
    def test_pass_code(self):
        result = check_borrow_source('int x = 1;')
        self.assertEqual((result.status, result.code), (BorrowStatus.PASS, 'BORROW_PASS'))

    def test_unsupported_code(self):
        result = check_borrow_source('print(1);')
        self.assertEqual((result.status, result.code), (BorrowStatus.UNSUPPORTED, 'UNSUPPORTED_CONSTRUCT'))

    def test_undefined_code(self):
        result = check_borrow_source('int x = missing;')
        self.assertEqual((result.status, result.code), (BorrowStatus.ERROR, 'BORROW_ERROR'))

    def test_scope_code(self):
        result = check_borrow_source('if (true) { int temp = 1; } int x = temp;')
        self.assertEqual((result.status, result.code), (BorrowStatus.ERROR, 'BORROW_ERROR'))

    def test_unsupported_is_typed(self):
        with self.assertRaises(UnsupportedBorrowError):
            self._unsupported()

    def _unsupported(self):
        from qrvm.borrow_source import analyze_borrow_source
        analyze_borrow_source('print(1);')

    def test_strict_error(self):
        with self.assertRaises(OwnershipError):
            require_borrow_source('int x = missing;')

    def test_strict_unsupported(self):
        with self.assertRaisesRegex(OwnershipError, 'UNSUPPORTED'):
            require_borrow_source('print(1);')

    def test_result_is_immutable(self):
        from dataclasses import FrozenInstanceError
        with self.assertRaises(FrozenInstanceError):
            check_borrow_source('int x = 1;').code = 'other'

    def test_invalid_input(self):
        with self.assertRaises(TypeError):
            check_borrow_source(None)

    def test_error_is_not_unsupported(self):
        result = check_borrow_source('int x = missing;')
        self.assertNotEqual(result.status, BorrowStatus.UNSUPPORTED)
