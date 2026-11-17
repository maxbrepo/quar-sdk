"""Chapter 5.22: semantic validation for fixed-signature indirect calls."""
import unittest
from frontend.quar.ast_nodes import FunctionReference, IndirectFunctionCall, Integer, String, Variable
from frontend.quar.errors import SemanticError
from frontend.quar.semantic import SemanticAnalyzer


class IndirectCallSemanticTests(unittest.TestCase):
    def setUp(self):
        self.analyzer = SemanticAnalyzer()

    def test_fixed_signature_result(self):
        call = IndirectFunctionCall(FunctionReference("sum"), [Integer(2), Integer(3)])
        self.assertEqual(self.analyzer.analyze_expression(call), "int")

    def test_wrong_arity(self):
        with self.assertRaisesRegex(SemanticError, "expects 2 arguments"):
            self.analyzer.analyze_expression(IndirectFunctionCall(FunctionReference("sum"), [Integer(2)]))

    def test_wrong_type(self):
        with self.assertRaisesRegex(SemanticError, "argument 1 expects"):
            self.analyzer.analyze_expression(IndirectFunctionCall(FunctionReference("sum"), [String("x"), Integer(2)]))

    def test_unknown_callee(self):
        with self.assertRaisesRegex(SemanticError, "known function reference"):
            self.analyzer.analyze_expression(IndirectFunctionCall(Variable("missing"), [Integer(2)]))

    def test_bound_reference(self):
        self.analyzer.bind_function_reference("callback", FunctionReference("sum"))
        call = IndirectFunctionCall(Variable("callback"), [Integer(2), Integer(3)])
        self.assertEqual(self.analyzer.analyze_expression(call), "int")

    def test_untyped_builtin_rejected(self):
        with self.assertRaisesRegex(SemanticError, "no fixed callable signature"):
            self.analyzer.analyze_expression(IndirectFunctionCall(FunctionReference("print"), [Integer(2)]))


if __name__ == "__main__":
    unittest.main()
