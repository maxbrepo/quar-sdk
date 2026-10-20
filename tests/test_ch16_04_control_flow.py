"""Regression tests for the conservative Control Flow Inspector."""
import unittest
from frontend.quar import ast_nodes as a
from qrvm.inspector_control_flow import inspect_control_flow
from qrvm.inspector_diagnostics import AnalysisStatus


def fn(body, return_type='int'):
    return a.FunctionDefinition(return_type, 'example', [], body)


class ControlFlowTests(unittest.TestCase):
    def test_direct_return(self):
        self.assertEqual(inspect_control_flow(fn([a.ReturnStatement(a.Integer(1))])).status, AnalysisStatus.PASS)

    def test_missing_return(self):
        self.assertTrue(inspect_control_flow(fn([])).has_errors)

    def test_if_both_branches_return(self):
        statement = a.IfStatement(a.Variable('flag'), [a.ReturnStatement(a.Integer(1))], [a.ReturnStatement(a.Integer(2))])
        self.assertEqual(inspect_control_flow(fn([statement])).status, AnalysisStatus.PASS)

    def test_if_one_branch_returns(self):
        statement = a.IfStatement(a.Variable('flag'), [a.ReturnStatement(a.Integer(1))], [])
        self.assertTrue(inspect_control_flow(fn([statement])).has_errors)

    def test_unreachable_after_return(self):
        result = inspect_control_flow(fn([a.ReturnStatement(a.Integer(1)), a.Assignment('x', a.Integer(2))]))
        self.assertIn('QI-CFG-002', [d.code for d in result.diagnostics])

    def test_constant_true_branch(self):
        statement = a.IfStatement(a.Boolean(True), [a.ReturnStatement(a.Integer(1))], [])
        result = inspect_control_flow(fn([statement]))
        self.assertEqual(result.status, AnalysisStatus.PASS)
        self.assertIn('QI-CFG-003', [d.code for d in result.diagnostics])

    def test_constant_false_branch(self):
        statement = a.IfStatement(a.Boolean(False), [a.ReturnStatement(a.Integer(1))], [])
        self.assertTrue(inspect_control_flow(fn([statement])).has_errors)

    def test_loop_return_not_guaranteed(self):
        statement = a.WhileStatement(a.Variable('flag'), [a.ReturnStatement(a.Integer(1))])
        self.assertTrue(inspect_control_flow(fn([statement])).has_errors)

    def test_unsupported_is_not_pass(self):
        self.assertEqual(inspect_control_flow(fn([a.BreakStatement()])).status, AnalysisStatus.UNSUPPORTED)

    def test_void_function_no_return(self):
        self.assertEqual(inspect_control_flow(fn([], 'void')).status, AnalysisStatus.PASS)


if __name__ == '__main__':
    unittest.main()
