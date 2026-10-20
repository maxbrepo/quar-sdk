import unittest
from qrvm.borrow_returns import summarize_source_returns
from qrvm.borrow_gate import check_borrow_source


class ReturnTests(unittest.TestCase):
    def summary(self, source):
        return summarize_source_returns(source)[0]

    def test_literal(self):
        self.assertEqual(self.summary('int f() { return 2; }').classification, 'SCALAR_VALUE')

    def test_parameter(self):
        self.assertEqual(self.summary('int f(int x) { return x; }').classification, 'SCALAR_VALUE')

    def test_local(self):
        self.assertEqual(self.summary('int f(int x) { int y = x + 1; return y; }').classification, 'SCALAR_VALUE')

    def test_unknown_name(self):
        self.assertEqual(self.summary('int f() { return missing; }').classification, 'UNKNOWN')

    def test_call_return(self):
        self.assertEqual(self.summary('int f() { return external(); }').classification, 'UNKNOWN')

    def test_void(self):
        self.assertEqual(self.summary('void f() { return; }').classification, 'UNKNOWN')

    def test_missing_return(self):
        self.assertEqual(self.summary('int f() { int x = 1; }').classification, 'UNKNOWN')

    def test_branch_returns(self):
        self.assertEqual(self.summary('int f(bool b) { if (b) { return 1; } else { return 2; } }').returns, 2)

    def test_inference_scalar(self):
        self.assertEqual(check_borrow_source('int f(int x) { return x + 1; } int y = f(1);', infer_local_calls=True).status.value, 'PASS')

    def test_inference_no_return(self):
        self.assertEqual(check_borrow_source('int f(int x) { int y = x; } int z = f(1);', infer_local_calls=True).status.value, 'UNSUPPORTED')

    def test_inference_unknown_return(self):
        self.assertEqual(check_borrow_source('int f(int x) { return missing; } int y = f(1);', infer_local_calls=True).status.value, 'UNSUPPORTED')


if __name__ == '__main__':
    unittest.main()
