import unittest
from qrvm.borrow_gate import BorrowStatus, check_borrow_source, require_borrow_source
from qrvm.ownership_analysis import OwnershipError
from main import build_frontend


class BorrowGateTests(unittest.TestCase):
    def test_pass(self):
        result = check_borrow_source('int x = 1; int y = x;')
        self.assertEqual(result.status, BorrowStatus.PASS)
        self.assertEqual(result.statements, 2)

    def test_expired_scope(self):
        result = check_borrow_source('if (true) { int temp = 1; } int x = temp;')
        self.assertEqual(result.status, BorrowStatus.ERROR)

    def test_undefined(self):
        self.assertEqual(check_borrow_source('int x = missing;').status, BorrowStatus.ERROR)

    def test_unsupported_print(self):
        self.assertEqual(check_borrow_source('print(1);').status, BorrowStatus.UNSUPPORTED)

    def test_strict_unsupported(self):
        with self.assertRaisesRegex(OwnershipError, 'UNSUPPORTED'):
            require_borrow_source('print(1);')

    def test_strict_error(self):
        with self.assertRaisesRegex(OwnershipError, 'ERROR'):
            require_borrow_source('int x = missing;')

    def test_strict_pass(self):
        self.assertEqual(require_borrow_source('int x = 1;').status, BorrowStatus.PASS)

    def test_frontend_default_unchanged(self):
        program, _ = build_frontend('print(1);')
        self.assertTrue(program)

    def test_frontend_opt_in_unsupported(self):
        with self.assertRaisesRegex(OwnershipError, 'UNSUPPORTED'):
            build_frontend('print(1);', borrow_check=True)

    def test_frontend_opt_in_pass(self):
        program, _ = build_frontend('int x = 1;', borrow_check=True)
        self.assertTrue(program)

    def test_invalid_input(self):
        with self.assertRaises(TypeError):
            check_borrow_source(None)

    def test_budget(self):
        self.assertEqual(check_borrow_source('int x = 1;', max_facts=1).status, BorrowStatus.ERROR)


if __name__ == '__main__':
    unittest.main()
