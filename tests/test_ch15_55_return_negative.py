"""Negative and unreachable-path checks for conservative return inference."""
import unittest
from qrvm.borrow_returns import summarize_source_returns


class ReturnSafetyBoundaryTests(unittest.TestCase):
    def classify(self, source):
        return summarize_source_returns(source)[0].classification

    def test_unreachable_unsupported_expression(self):
        self.assertEqual(self.classify('int f() { return 1; return unknown(); }'), 'SCALAR_VALUE')

    def test_unreachable_unsupported_statement(self):
        self.assertEqual(self.classify('int f() { return 1; while (true) { return 2; } }'), 'SCALAR_VALUE')

    def test_reachable_unsupported_expression_is_unknown(self):
        self.assertEqual(self.classify('int f() { return unknown(); }'), 'UNKNOWN')

    def test_partial_return_with_unknown_fallback_is_unknown(self):
        self.assertEqual(self.classify('int f(bool b) { if (b) { return 1; } return unknown(); }'), 'UNKNOWN')

    def test_non_scalar_return_not_certified(self):
        self.assertEqual(self.classify('int? f() { return none; }'), 'UNKNOWN')


if __name__ == '__main__':
    unittest.main()
