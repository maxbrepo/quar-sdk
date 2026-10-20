"""Inferred first assignments participate in lexical symbol tracking."""
import unittest

from frontend.quar.ast_nodes import Assignment, Integer
from frontend.quar.semantic import SemanticAnalyzer


class InferredBindingBridgeTests(unittest.TestCase):
    def test_first_assignment_creates_binding(self):
        analyzer = SemanticAnalyzer()
        analyzer.analyze_assignment(Assignment("count", Integer(1)))
        first = analyzer.lexical_bindings.resolve_required("count")
        analyzer.analyze_assignment(Assignment("count", Integer(2)))
        self.assertEqual(analyzer.lexical_bindings.resolve_required("count"), first)

    def test_nested_assignment_uses_outer_binding(self):
        analyzer = SemanticAnalyzer()
        analyzer.analyze_assignment(Assignment("count", Integer(1)))
        outer = analyzer.lexical_bindings.resolve_required("count")
        analyzer.analyze_scoped_block([Assignment("count", Integer(2))])
        self.assertEqual(analyzer.lexical_bindings.resolve_required("count"), outer)

    def test_nested_first_assignment_does_not_escape(self):
        analyzer = SemanticAnalyzer()
        analyzer.analyze_scoped_block([Assignment("local", Integer(1))])
        self.assertIsNone(analyzer.lexical_bindings.resolve("local"))
        self.assertNotIn("local", analyzer.variables)


if __name__ == "__main__":
    unittest.main()
