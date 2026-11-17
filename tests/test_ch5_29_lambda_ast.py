"""Structural checks for the experimental capture-free lambda AST."""
import unittest

from frontend.quar.ast_nodes import FunctionParameter, LambdaExpression, ReturnStatement, Variable


class LambdaAstTests(unittest.TestCase):
    def test_capture_free_lambda_preserves_signature_and_body(self):
        parameter = FunctionParameter('int', 'x')
        body = [ReturnStatement(Variable('x'))]
        node = LambdaExpression([parameter], 'int', body)
        self.assertEqual(node.parameters, [parameter])
        self.assertEqual(node.return_type, 'int')
        self.assertEqual(node.body, body)

    def test_zero_argument_void_lambda(self):
        node = LambdaExpression([], 'void', [])
        self.assertEqual(node.parameters, [])
        self.assertEqual(node.return_type, 'void')


if __name__ == '__main__':
    unittest.main()
