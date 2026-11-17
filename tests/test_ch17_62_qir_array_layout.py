"""Parity and rejection tests for the initial fixed-array layout contract."""
import unittest

from frontend.quar.ast_nodes import ArrayDeclaration, Integer
from frontend.quar.ir.builder import lower_statement
from frontend.quar.qir.array_layout import analyze_array_layout, QIRArrayLayoutError


class ArrayLayoutTests(unittest.TestCase):
    def test_ast_and_legacy_layout_parity(self):
        ast = ArrayDeclaration('i32', 'items', 3, [Integer(2), Integer(-4), Integer(6)])
        self.assertEqual(analyze_array_layout(ast), analyze_array_layout(lower_statement(ast)))
        self.assertEqual(analyze_array_layout(ast).initial_values, (2, -4, 6))

    def test_empty_array_rejected(self):
        with self.assertRaisesRegex(QIRArrayLayoutError, 'positive'):
            analyze_array_layout(ArrayDeclaration('i32', 'items', 0, []))

    def test_mismatched_initializer_count_rejected(self):
        with self.assertRaisesRegex(QIRArrayLayoutError, 'count'):
            analyze_array_layout(ArrayDeclaration('i32', 'items', 2, [Integer(1)]))

    def test_dynamic_and_multidimensional_rejected(self):
        for declaration in (ArrayDeclaration('i32', 'items', 2, [Integer(1), Integer(2)], dynamic=True),
                            ArrayDeclaration('i32', 'items', 2, [Integer(1), Integer(2)], second_size=2)):
            with self.subTest(declaration=declaration), self.assertRaises(QIRArrayLayoutError):
                analyze_array_layout(declaration)

    def test_out_of_range_value_rejected(self):
        with self.assertRaisesRegex(QIRArrayLayoutError, 'i32'):
            analyze_array_layout(ArrayDeclaration('i32', 'items', 1, [Integer(2**31)]))

    def test_non_literal_initializer_rejected(self):
        with self.assertRaisesRegex(QIRArrayLayoutError, 'literals'):
            analyze_array_layout(ArrayDeclaration('i32', 'items', 1, [object()]))


if __name__ == '__main__':
    unittest.main()
