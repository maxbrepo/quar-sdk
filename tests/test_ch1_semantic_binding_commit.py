"""Keep the semantic type table and lexical registry consistent on errors."""
import unittest

from frontend.quar.ast_nodes import Assignment, Integer, String, VariableDeclaration
from frontend.quar.errors import SemanticError
from frontend.quar.semantic import SemanticAnalyzer


class SemanticBindingCommitTests(unittest.TestCase):
    def test_failed_typed_declaration_does_not_register_binding(self):
        analyzer = SemanticAnalyzer()
        with self.assertRaises(SemanticError):
            analyzer.analyze_variable_declaration(VariableDeclaration("i32", "value", String("wrong")))
        self.assertNotIn("value", analyzer.variables)
        self.assertIsNone(analyzer.lexical_bindings.resolve("value"))

    def test_duplicate_lexical_binding_does_not_change_type_table(self):
        analyzer = SemanticAnalyzer()
        original = analyzer.lexical_bindings.declare("value")
        with self.assertRaisesRegex(SemanticError, "already declared"):
            analyzer.analyze_variable_declaration(VariableDeclaration("i32", "value", Integer(1)))
        self.assertEqual(analyzer.lexical_bindings.resolve("value"), original)
        self.assertNotIn("value", analyzer.variables)

    def test_inferred_assignment_rejects_inconsistent_symbol_tables(self):
        analyzer = SemanticAnalyzer()
        original = analyzer.lexical_bindings.declare("value")
        with self.assertRaisesRegex(SemanticError, "already declared"):
            analyzer.analyze_assignment(Assignment("value", Integer(1)))
        self.assertEqual(analyzer.lexical_bindings.resolve("value"), original)
        self.assertNotIn("value", analyzer.variables)


if __name__ == "__main__":
    unittest.main()
