"""Bounds contract tests before introducing executable QIR indexed memory."""
import unittest

from frontend.quar.ast_nodes import ArrayDeclaration, Integer
from frontend.quar.ir.builder import lower_statement
from frontend.quar.qir.array_layout import analyze_array_layout
from frontend.quar.qir.array_index import (
    QIRArrayIndexError, check_constant_index, runtime_index_check,
)


class ArrayIndexContractTests(unittest.TestCase):
    def setUp(self):
        ast = ArrayDeclaration('i32', 'items', 3, [Integer(4), Integer(5), Integer(6)])
        self.layouts = (analyze_array_layout(ast), analyze_array_layout(lower_statement(ast)))

    def test_first_and_last_valid_indices(self):
        for layout in self.layouts:
            with self.subTest(layout=layout):
                self.assertEqual(check_constant_index(layout, 0), 0)
                self.assertEqual(check_constant_index(layout, 2), 2)

    def test_negative_index_rejected(self):
        for layout in self.layouts:
            with self.assertRaises(QIRArrayIndexError):
                check_constant_index(layout, -1)

    def test_one_past_end_rejected(self):
        for layout in self.layouts:
            with self.assertRaises(QIRArrayIndexError):
                check_constant_index(layout, 3)

    def test_non_integer_index_rejected(self):
        for layout in self.layouts:
            for value in (True, 1.0, '1'):
                with self.subTest(value=value), self.assertRaises(QIRArrayIndexError):
                    check_constant_index(layout, value)

    def test_runtime_obligation_bounds(self):
        for layout in self.layouts:
            check = runtime_index_check(layout)
            self.assertEqual((check.lower_bound, check.length), (0, 3))
            self.assertTrue(check.contains(1))
            self.assertFalse(check.contains(-1))
            self.assertFalse(check.contains(3))


if __name__ == '__main__':
    unittest.main()
