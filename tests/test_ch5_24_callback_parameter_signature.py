"""Internal callback-parameter signature checks; source syntax is not implemented."""
import unittest
from frontend.quar.ast_nodes import (FunctionDefinition, FunctionParameter, IndirectFunctionCall, Integer, ReturnStatement, Variable)
from frontend.quar.errors import SemanticError
from frontend.quar.function_types import FunctionSignature
from frontend.quar.semantic import SemanticAnalyzer


class CallbackParameterSignatureTests(unittest.TestCase):
    def test_typed_callback_body(self):
        analyzer = SemanticAnalyzer()
        callback = FunctionParameter('function', 'callback', callback_signature=FunctionSignature(('int',), 'int'))
        function = FunctionDefinition('int', 'apply', [callback], [ReturnStatement(IndirectFunctionCall(Variable('callback'), [Integer(42)]))])
        analyzer.register_function(function)
        analyzer.analyze_function_definition(function)

    def test_wrong_callback_argument_is_rejected(self):
        analyzer = SemanticAnalyzer()
        callback = FunctionParameter('function', 'callback', callback_signature=FunctionSignature(('int', 'int'), 'int'))
        function = FunctionDefinition('int', 'apply', [callback], [ReturnStatement(IndirectFunctionCall(Variable('callback'), [Integer(42)]))])
        analyzer.register_function(function)
        with self.assertRaisesRegex(SemanticError, 'expects 2 arguments'):
            analyzer.analyze_function_definition(function)

    def test_invalid_nonfunction_annotation(self):
        analyzer = SemanticAnalyzer()
        callback = FunctionParameter('int', 'callback', callback_signature=FunctionSignature(('int',), 'int'))
        function = FunctionDefinition('int', 'apply', [callback], [ReturnStatement(Integer(42))])
        analyzer.register_function(function)
        with self.assertRaisesRegex(SemanticError, "must have type 'function'"):
            analyzer.analyze_function_definition(function)


if __name__ == '__main__':
    unittest.main()
