"""Chapter 5.18: inferred function references in semantic variable bindings."""
import unittest
from frontend.quar.ast_nodes import Assignment, FunctionReference, Integer, Variable
from frontend.quar.errors import SemanticError
from frontend.quar.semantic import SemanticAnalyzer


class InferredFunctionBindingsTests(unittest.TestCase):
    def test_inferred_binding_records_signature(self):
        analyzer = SemanticAnalyzer()
        analyzer.analyze_assignment(Assignment('operation', FunctionReference('sum')))
        self.assertEqual(analyzer.variables['operation'], 'function')
        self.assertEqual(analyzer.bound_function_signature('operation').return_type, 'int')

    def test_copy_preserves_signature(self):
        analyzer = SemanticAnalyzer()
        analyzer.analyze_assignment(Assignment('first', FunctionReference('sum')))
        analyzer.analyze_assignment(Assignment('second', Variable('first')))
        self.assertEqual(analyzer.bound_function_signature('first'), analyzer.bound_function_signature('second'))

    def test_non_function_reassignment_rejected(self):
        analyzer = SemanticAnalyzer()
        analyzer.analyze_assignment(Assignment('operation', FunctionReference('sum')))
        with self.assertRaises(SemanticError):
            analyzer.analyze_assignment(Assignment('operation', Integer(1)))
        self.assertIn('operation', analyzer.function_bindings)

    def test_unknown_reference_does_not_commit_variable(self):
        analyzer = SemanticAnalyzer()
        with self.assertRaises(SemanticError):
            analyzer.analyze_assignment(Assignment('operation', FunctionReference('missing_function')))
        self.assertNotIn('operation', analyzer.variables)
        self.assertNotIn('operation', analyzer.function_bindings)

    def test_scope_restores_inferred_bindings(self):
        analyzer = SemanticAnalyzer()
        def visit(statement):
            analyzer.analyze_assignment(statement)
        analyzer.analyze_statement = visit
        analyzer.analyze_scoped_block([Assignment('temporary', FunctionReference('sum'))])
        self.assertNotIn('temporary', analyzer.function_bindings)
        self.assertNotIn('temporary', analyzer.variables)


if __name__ == '__main__':
    unittest.main()
