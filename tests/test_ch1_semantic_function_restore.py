"""Semantic function environments must recover after invalid parameters."""
import unittest

from frontend.quar.ast_nodes import FunctionDefinition, FunctionParameter
from frontend.quar.errors import SemanticError
from frontend.quar.semantic import SemanticAnalyzer


class SemanticFunctionRestoreTests(unittest.TestCase):
    def test_duplicate_parameter_restores_outer_environment(self):
        analyzer = SemanticAnalyzer()
        analyzer.variables["outer"] = "i32"
        analyzer.arrays["existing"] = "array"
        analyzer.objects["instance"] = "object"
        analyzer.current_return_type = "void"
        function = FunctionDefinition(
            "void", "broken",
            [FunctionParameter("i32", "item"), FunctionParameter("i32", "item")],
            [],
        )
        with self.assertRaises(SemanticError):
            analyzer.analyze_function_definition(function)
        self.assertEqual(analyzer.variables, {"outer": "i32"})
        self.assertEqual(analyzer.arrays, {"existing": "array"})
        self.assertEqual(analyzer.objects, {"instance": "object"})
        self.assertEqual(analyzer.current_return_type, "void")


if __name__ == "__main__":
    unittest.main()
