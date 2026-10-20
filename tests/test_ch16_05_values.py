"""Regression tests for the conservative constant-value inspector."""
import unittest
from frontend.quar import ast_nodes as a
from qrvm.inspector_diagnostics import AnalysisStatus
from qrvm.inspector_values import inspect_values


class ValueInspectorTests(unittest.TestCase):
    def check(self, expr):
        return inspect_values([a.ReturnStatement(expr)])

    def test_literal_zero_divisor(self):
        self.assertTrue(self.check(a.BinaryOperation(a.Integer(4), '/', a.Integer(0))).has_errors)

    def test_computed_zero_divisor(self):
        expr = a.BinaryOperation(a.Integer(8), '/', a.BinaryOperation(a.Integer(3), '-', a.Integer(3)))
        self.assertIn('QI-VAL-001', [d.code for d in self.check(expr).diagnostics])

    def test_unknown_numerator_still_finds_zero(self):
        self.assertTrue(self.check(a.BinaryOperation(a.Variable('x'), '/', a.Integer(0))).has_errors)

    def test_modulo_zero(self):
        self.assertTrue(self.check(a.BinaryOperation(a.Integer(5), '%', a.Integer(0))).has_errors)

    def test_nonzero_divisor(self):
        self.assertEqual(self.check(a.BinaryOperation(a.Integer(4), '/', a.Integer(2))).status, AnalysisStatus.PASS)

    def test_unknown_divisor_not_falsely_flagged(self):
        self.assertFalse(self.check(a.BinaryOperation(a.Integer(4), '/', a.Variable('x'))).has_errors)

    def test_nested_branch(self):
        body = [a.IfStatement(a.Variable('flag'), [a.ReturnStatement(a.BinaryOperation(a.Integer(1), '/', a.Integer(0)))], [])]
        self.assertTrue(inspect_values(body).has_errors)

    def test_unsupported_expression_not_pass(self):
        self.assertEqual(self.check(a.FunctionCall('f', [])).status, AnalysisStatus.UNSUPPORTED)


if __name__ == '__main__':
    unittest.main()
