"""Semantic name resolution for experimental function references."""
import unittest
from frontend.quar.ast_nodes import FunctionReference
from frontend.quar.errors import SemanticError
from frontend.quar.semantic import SemanticAnalyzer


class FunctionReferenceSemanticTests(unittest.TestCase):
    def test_known_builtin_function(self):
        self.assertEqual(SemanticAnalyzer().analyze_expression(FunctionReference("print")), "function")

    def test_unknown_function_is_rejected(self):
        with self.assertRaisesRegex(SemanticError, "Unknown function reference"):
            SemanticAnalyzer().analyze_expression(FunctionReference("missing"))

    def test_registered_function_signature_is_unchanged(self):
        analyzer = SemanticAnalyzer()
        original = analyzer.functions["sum"].copy()
        self.assertEqual(analyzer.analyze_expression(FunctionReference("sum")), "function")
        self.assertEqual(analyzer.functions["sum"], original)


if __name__ == "__main__":
    unittest.main()
