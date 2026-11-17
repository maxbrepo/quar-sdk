"""Chapter 5.16: isolated semantic groundwork for callable variable bindings."""
import unittest

from frontend.quar.ast_nodes import FunctionReference
from frontend.quar.errors import SemanticError
from frontend.quar.function_types import FunctionSignature
from frontend.quar.semantic import SemanticAnalyzer


class FunctionBindingPreparationTests(unittest.TestCase):
    def test_binding_records_signature(self):
        analyzer = SemanticAnalyzer()
        signature = analyzer.bind_function_reference("operation", FunctionReference("sum"))
        self.assertEqual(signature, FunctionSignature(("int", "int"), "int"))
        self.assertEqual(analyzer.function_bindings["operation"], signature)

    def test_exact_expected_signature(self):
        analyzer = SemanticAnalyzer()
        expected = FunctionSignature(("int", "int"), "int")
        self.assertEqual(analyzer.bind_function_reference("f", FunctionReference("sum"), expected), expected)

    def test_mismatch_does_not_register(self):
        analyzer = SemanticAnalyzer()
        with self.assertRaisesRegex(SemanticError, "Incompatible function signature"):
            analyzer.bind_function_reference("f", FunctionReference("sum"), FunctionSignature(("string",), "void"))
        self.assertNotIn("f", analyzer.function_bindings)

    def test_dynamic_builtin_rejected_without_partial_binding(self):
        analyzer = SemanticAnalyzer()
        with self.assertRaisesRegex(SemanticError, "no fixed callable signature"):
            analyzer.bind_function_reference("f", FunctionReference("print"))
        self.assertNotIn("f", analyzer.function_bindings)

    def test_duplicate_binding_rejected(self):
        analyzer = SemanticAnalyzer()
        analyzer.bind_function_reference("f", FunctionReference("sum"))
        with self.assertRaisesRegex(SemanticError, "already declared"):
            analyzer.bind_function_reference("f", FunctionReference("sum"))


if __name__ == "__main__":
    unittest.main()
