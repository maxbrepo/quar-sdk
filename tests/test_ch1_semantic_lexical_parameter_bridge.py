"""Function parameters receive lexical identities without leaking scopes."""
import unittest

from frontend.quar.ast_nodes import FunctionDefinition, FunctionParameter
from frontend.quar.errors import SemanticError
from frontend.quar.semantic import SemanticAnalyzer


class SemanticLexicalParameterBridgeTests(unittest.TestCase):
    def test_function_parameters_are_isolated_from_outer_bindings(self):
        analyzer = SemanticAnalyzer()
        outer = analyzer.lexical_bindings.declare("value")
        function = FunctionDefinition("void", "demo", [FunctionParameter("i32", "value")], [])
        analyzer.analyze_function_definition(function)
        self.assertEqual(analyzer.lexical_bindings.resolve_required("value"), outer)
        self.assertEqual(analyzer.lexical_bindings.depth, 0)

    def test_duplicate_parameter_does_not_leak_lexical_scope(self):
        analyzer = SemanticAnalyzer()
        function = FunctionDefinition("void", "broken", [
            FunctionParameter("i32", "same"), FunctionParameter("i32", "same")
        ], [])
        with self.assertRaisesRegex(SemanticError, "already declared"):
            analyzer.analyze_function_definition(function)
        self.assertIsNone(analyzer.lexical_bindings.resolve("same"))
        self.assertEqual(analyzer.lexical_bindings.depth, 0)


if __name__ == "__main__":
    unittest.main()
