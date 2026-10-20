"""Regression tests for conservative function effect summaries."""
import unittest
from frontend.quar import ast_nodes as a
from qrvm.borrow_effects import summarize_function_effect, summarize_source_effects
from qrvm.borrow_gate import check_borrow_source, BorrowStatus


def fn(body, parameters=(), name='f'):
    return a.FunctionDefinition('int', name, list(parameters), list(body))


class BorrowEffectsTests(unittest.TestCase):
    def test_constant_return(self):
        self.assertEqual(summarize_function_effect(fn([a.ReturnStatement(a.Integer(1))])).classification, 'LOCAL_READ_ONLY')

    def test_parameter_read(self):
        p = a.FunctionParameter('int', 'x')
        self.assertEqual(summarize_function_effect(fn([a.ReturnStatement(a.Variable('x'))], [p])).classification, 'LOCAL_READ_ONLY')

    def test_unknown_call(self):
        self.assertEqual(summarize_function_effect(fn([a.ReturnStatement(a.FunctionCall('external', []))])).classification, 'UNKNOWN')

    def test_recursive_call_unknown(self):
        self.assertEqual(summarize_function_effect(fn([a.ReturnStatement(a.FunctionCall('f', []))])).classification, 'UNKNOWN')

    def test_unbound_read(self):
        self.assertEqual(summarize_function_effect(fn([a.ReturnStatement(a.Variable('missing'))])).classification, 'UNKNOWN')

    def test_global_write(self):
        self.assertEqual(summarize_function_effect(fn([a.Assignment('global', a.Integer(2))])).classification, 'UNKNOWN')

    def test_parameter_write(self):
        p = a.FunctionParameter('int', 'x')
        self.assertEqual(summarize_function_effect(fn([a.Assignment('x', a.Integer(2))], [p])).classification, 'UNKNOWN')

    def test_local_write(self):
        body = [a.VariableDeclaration('int','x',a.Integer(1)), a.Assignment('x',a.Integer(2)), a.ReturnStatement(a.Variable('x'))]
        self.assertEqual(summarize_function_effect(fn(body)).classification, 'LOCAL_READ_ONLY')

    def test_branch_local_expiry(self):
        body = [a.IfStatement(a.Boolean(True), [a.VariableDeclaration('int','x',a.Integer(1))], []), a.ReturnStatement(a.Variable('x'))]
        self.assertEqual(summarize_function_effect(fn(body)).classification, 'UNKNOWN')

    def test_shadowing_unknown(self):
        body = [a.VariableDeclaration('int','x',a.Integer(1)), a.VariableDeclaration('int','x',a.Integer(2))]
        self.assertEqual(summarize_function_effect(fn(body)).classification, 'UNKNOWN')

    def test_non_scalar_unknown(self):
        self.assertEqual(summarize_function_effect(a.FunctionDefinition('object','f',[],[])).classification, 'UNKNOWN')

    def test_no_auto_trust(self):
        self.assertEqual(check_borrow_source('int x = f(1);').status, BorrowStatus.UNSUPPORTED)

    def test_parse_source(self):
        effects = summarize_source_effects('int f(int x) { return x + 1; }')
        self.assertEqual(effects[0].classification, 'LOCAL_READ_ONLY')


if __name__ == '__main__':
    unittest.main()
