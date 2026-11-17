"""Chapter 5.15: signature validation for function reference expressions."""
import unittest

from frontend.quar.ast_nodes import FunctionReference
from frontend.quar.errors import SemanticError
from frontend.quar.semantic import SemanticAnalyzer
from frontend.quar.function_types import FunctionSignature


class FunctionReferenceSignatureTests(unittest.TestCase):
    def test_fixed_builtin_reference_is_accepted(self):
        analyzer = SemanticAnalyzer()
        reference = FunctionReference("sum")
        self.assertEqual(analyzer.analyze_expression(reference), "function")
        self.assertEqual(analyzer.reference_signature(reference), FunctionSignature(("int", "int"), "int"))

    def test_non_reference_is_rejected(self):
        with self.assertRaisesRegex(SemanticError, "Expected a function reference"):
            SemanticAnalyzer().reference_signature("sum")

    def test_untyped_builtin_reference_is_recognized_but_not_fixed(self):
        analyzer = SemanticAnalyzer()
        self.assertEqual(analyzer.analyze_expression(FunctionReference("print")), "function")
        with self.assertRaisesRegex(SemanticError, "no fixed callable signature"):
            analyzer.reference_signature(FunctionReference("print"))

    def test_unknown_reference_is_rejected(self):
        with self.assertRaisesRegex(SemanticError, "Unknown function reference"):
            SemanticAnalyzer().analyze_expression(FunctionReference("not_defined"))


if __name__ == "__main__":
    unittest.main()
