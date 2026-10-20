"""Conservative, explicitly trusted call-expression analysis."""
import unittest
from frontend.quar import ast_nodes as a
from qrvm.borrow_gate import BorrowStatus, check_borrow_source
from qrvm.borrow_scoped_cfg import analyze_scoped_cfg
from qrvm.ownership_analysis import OwnershipError


class BorrowCallsTests(unittest.TestCase):
    def test_unknown_call_is_unsupported(self):
        d = check_borrow_source('int x = 1; int y = foo(x);')
        self.assertEqual(d.status, BorrowStatus.UNSUPPORTED)

    def test_explicitly_trusted_call(self):
        d = check_borrow_source('int x = 1; int y = foo(x);', pure_calls=('foo',))
        self.assertEqual(d.status, BorrowStatus.PASS)

    def test_unknown_nested_call_rejected(self):
        d = check_borrow_source('int x = 1; int y = foo(bar(x));', pure_calls=('foo',))
        self.assertEqual(d.status, BorrowStatus.UNSUPPORTED)

    def test_nested_trusted_calls(self):
        d = check_borrow_source('int x = 1; int y = foo(bar(x));', pure_calls=('foo','bar'))
        self.assertEqual(d.status, BorrowStatus.PASS)

    def test_missing_argument_rejected(self):
        d = check_borrow_source('int y = foo(missing);', pure_calls=('foo',))
        self.assertEqual(d.status, BorrowStatus.ERROR)

    def test_named_argument_ast(self):
        stmts = [a.VariableDeclaration('int','x',a.Integer(1)), a.VariableDeclaration('int','y',a.FunctionCall('foo',[a.NamedArgument('value',a.Variable('x'))]))]
        analyze_scoped_cfg(stmts, pure_calls=('foo',))

    def test_missing_named_argument_ast(self):
        stmts = [a.VariableDeclaration('int','y',a.FunctionCall('foo',[a.NamedArgument('value',a.Variable('missing'))]))]
        with self.assertRaises(OwnershipError):
            analyze_scoped_cfg(stmts, pure_calls=('foo',))

    def test_call_in_condition(self):
        d = check_borrow_source('int x = 1; if (foo(x)) { int y = x; }', pure_calls=('foo',))
        self.assertEqual(d.status, BorrowStatus.PASS)

    def test_call_in_assignment(self):
        d = check_borrow_source('int x = 1; x = foo(x);', pure_calls=('foo',))
        self.assertEqual(d.status, BorrowStatus.PASS)

    def test_invalid_pure_call_names(self):
        with self.assertRaises(ValueError):
            analyze_scoped_cfg([], pure_calls='foo')

    def test_default_unchanged(self):
        self.assertEqual(check_borrow_source('int x = 1;').status, BorrowStatus.PASS)

    def test_unknown_call_not_error(self):
        self.assertEqual(check_borrow_source('int x = foo(1);').code, 'UNSUPPORTED_CONSTRUCT')


if __name__ == '__main__':
    unittest.main()
