"""Chapter 5.17: experimental function bindings respect semantic scopes."""
import unittest
from frontend.quar.ast_nodes import FunctionReference, FunctionDefinition
from frontend.quar.errors import SemanticError
from frontend.quar.semantic import SemanticAnalyzer


class FunctionBindingScopeTests(unittest.TestCase):
    def test_binding_visible_in_own_scope(self):
        analyzer = SemanticAnalyzer()
        expected = analyzer.bind_function_reference('operation', FunctionReference('sum'))
        self.assertEqual(analyzer.bound_function_signature('operation'), expected)

    def test_nested_scope_restores_bindings(self):
        analyzer = SemanticAnalyzer()
        analyzer.bind_function_reference('outer', FunctionReference('sum'))
        def visit(_statement):
            self.assertEqual(analyzer.bound_function_signature('outer').return_type, 'int')
            analyzer.bind_function_reference('inner', FunctionReference('sum'))
        analyzer.analyze_statement = visit
        analyzer.analyze_scoped_block([object()])
        self.assertIn('outer', analyzer.function_bindings)
        self.assertNotIn('inner', analyzer.function_bindings)

    def test_exception_restores_bindings(self):
        analyzer = SemanticAnalyzer()
        def visit(_statement):
            analyzer.bind_function_reference('temporary', FunctionReference('sum'))
            raise RuntimeError('test error')
        analyzer.analyze_statement = visit
        with self.assertRaisesRegex(RuntimeError, 'test error'):
            analyzer.analyze_scoped_block([object()])
        self.assertNotIn('temporary', analyzer.function_bindings)

    def test_unknown_binding_rejected(self):
        with self.assertRaisesRegex(SemanticError, 'Unknown function binding'):
            SemanticAnalyzer().bound_function_signature('missing')


if __name__ == '__main__':
    unittest.main()
