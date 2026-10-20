"""Regression tests for conservative return-path inference."""
import unittest
from qrvm.borrow_returns import summarize_source_returns


class ReturnPathTests(unittest.TestCase):
    def classify(self, source):
        return summarize_source_returns(source)[0].classification

    def test_partial_if(self):
        self.assertEqual(self.classify('int f(bool b) { if (b) { return 1; } }'), 'UNKNOWN')

    def test_complete_if(self):
        self.assertEqual(self.classify('int f(bool b) { if (b) { return 1; } else { return 2; } }'), 'SCALAR_VALUE')

    def test_return_after_partial_if(self):
        self.assertEqual(self.classify('int f(bool b) { if (b) { return 1; } return 2; }'), 'SCALAR_VALUE')

    def test_loop_only_return(self):
        self.assertEqual(self.classify('int f(bool b) { while (b) { return 1; } }'), 'UNKNOWN')

    def test_loop_followed_by_return(self):
        self.assertEqual(self.classify('int f(bool b) { while (b) { return 1; } return 2; }'), 'SCALAR_VALUE')


if __name__ == '__main__':
    unittest.main()
