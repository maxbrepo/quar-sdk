"""Chapter 5.14: callable signature model without changing runtime semantics."""
import unittest
from frontend.quar.errors import SemanticError
from frontend.quar.function_types import FunctionSignature
from frontend.quar.semantic import SemanticAnalyzer


class FunctionSignatureTests(unittest.TestCase):
    def test_fixed_builtin_signature(self):
        self.assertEqual(SemanticAnalyzer().function_signature('sum'), FunctionSignature(('int', 'int'), 'int'))

    def test_untyped_builtin_is_not_assumed_fixed(self):
        with self.assertRaisesRegex(SemanticError, 'no fixed callable signature'):
            SemanticAnalyzer().function_signature('print')

    def test_unknown_function(self):
        with self.assertRaisesRegex(SemanticError, 'Unknown function reference'):
            SemanticAnalyzer().function_signature('missing')

    def test_signature_equality(self):
        signature = FunctionSignature(('int',), 'bool')
        self.assertTrue(signature.is_compatible_with(FunctionSignature(('int',), 'bool')))
        self.assertFalse(signature.is_compatible_with(FunctionSignature(('bool',), 'bool')))
        self.assertFalse(signature.is_compatible_with(FunctionSignature(('int',), 'int')))

    def test_signature_is_immutable(self):
        with self.assertRaises(AttributeError):
            FunctionSignature(('int',), 'int').return_type = 'void'


if __name__ == '__main__':
    unittest.main()
