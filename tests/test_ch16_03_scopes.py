"""Regression tests for lexical-scope symbol analysis."""
import unittest
from frontend.quar import ast_nodes as a
from qrvm.inspector_scopes import inspect_scopes
from qrvm.inspector_diagnostics import AnalysisStatus


class ScopeInspectorTests(unittest.TestCase):
    def test_outer_variable_visible_in_branch(self):
        r = inspect_scopes([a.VariableDeclaration('int', 'x', a.Integer(1)), a.IfStatement(a.Boolean(True), [a.ReturnStatement(a.Variable('x'))], [])])
        self.assertEqual(r.status, AnalysisStatus.PASS)

    def test_branch_local_does_not_escape(self):
        r = inspect_scopes([a.IfStatement(a.Boolean(True), [a.VariableDeclaration('int', 'x', a.Integer(1))], []), a.ReturnStatement(a.Variable('x'))])
        self.assertTrue(r.has_errors)

    def test_sibling_branches_can_reuse_name(self):
        r = inspect_scopes([a.IfStatement(a.Boolean(True), [a.VariableDeclaration('int', 'x', a.Integer(1))], [a.VariableDeclaration('int', 'x', a.Integer(2))])])
        self.assertEqual(r.status, AnalysisStatus.PASS)

    def test_duplicate_in_same_scope(self):
        r = inspect_scopes([a.VariableDeclaration('int', 'x', a.Integer(1)), a.VariableDeclaration('int', 'x', a.Integer(2))])
        self.assertTrue(r.has_errors)

    def test_loop_local_does_not_escape(self):
        r = inspect_scopes([a.WhileStatement(a.Boolean(True), [a.VariableDeclaration('int', 'i', a.Integer(1))]), a.ReturnStatement(a.Variable('i'))])
        self.assertTrue(r.has_errors)

    def test_loop_can_read_outer_variable(self):
        r = inspect_scopes([a.VariableDeclaration('int', 'i', a.Integer(1)), a.WhileStatement(a.Variable('i'), [a.Assignment('i', a.Integer(2))])])
        self.assertEqual(r.status, AnalysisStatus.PASS)

    def test_unsupported_is_not_pass(self):
        r = inspect_scopes([a.BreakStatement()])
        self.assertEqual(r.status, AnalysisStatus.UNSUPPORTED)

    def test_parameters_are_visible(self):
        r = inspect_scopes([a.ReturnStatement(a.Variable('arg'))], parameters=('arg',))
        self.assertEqual(r.status, AnalysisStatus.PASS)


if __name__ == '__main__':
    unittest.main()
