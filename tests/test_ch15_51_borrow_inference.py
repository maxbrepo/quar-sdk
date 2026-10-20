"""Opt-in conservative local function inference tests."""
import unittest
from qrvm.borrow_gate import check_borrow_source, BorrowStatus


class InferenceTests(unittest.TestCase):
    def check(self, source, infer=False):
        return check_borrow_source(source, infer_local_calls=infer).status

    def test_opt_in_default(self):
        self.assertEqual(self.check('int f(int x) { return x+1; } int y = f(2);'), BorrowStatus.UNSUPPORTED)

    def test_certified_call(self):
        self.assertEqual(self.check('int f(int x) { return x+1; } int y = f(2);', True), BorrowStatus.PASS)

    def test_unknown_function(self):
        self.assertEqual(self.check('int y = external(2);', True), BorrowStatus.UNSUPPORTED)

    def test_nested_calls(self):
        self.assertEqual(self.check('int f(int x) { return x+1; } int y = f(f(2));', True), BorrowStatus.PASS)

    def test_unbound_argument(self):
        self.assertEqual(self.check('int f(int x) { return x+1; } int y = f(missing);', True), BorrowStatus.ERROR)

    def test_wrong_arity(self):
        self.assertEqual(self.check('int f(int x) { return x+1; } int y = f();', True), BorrowStatus.UNSUPPORTED)

    def test_impure_function(self):
        self.assertEqual(self.check('int f(int x) { return external(x); } int y = f(2);', True), BorrowStatus.UNSUPPORTED)

    def test_function_only(self):
        self.assertEqual(self.check('int f(int x) { return x+1; }', True), BorrowStatus.PASS)

    def test_duplicate(self):
        self.assertEqual(self.check('int f(int x) { return x; } int f(int y) { return y; }', True), BorrowStatus.UNSUPPORTED)

    def test_branch_call(self):
        self.assertEqual(self.check('int f(int x) { return x; } if (true) { int y = f(1); }', True), BorrowStatus.PASS)

    def test_existing_source(self):
        self.assertEqual(self.check('int x = 1;', True), BorrowStatus.PASS)


if __name__ == '__main__':
    unittest.main()
