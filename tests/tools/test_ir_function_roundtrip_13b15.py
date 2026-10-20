"""Function definitions must cross the IR boundary without retaining source AST."""
import unittest

from frontend.quar.ast_nodes import (FunctionDefinition, FunctionParameter, Integer,
    Variable, BinaryOperation, ReturnStatement, FunctionCall, VariableDeclaration)
from frontend.quar.ir.builder import lower_statement
from frontend.quar.ir.model import IRFunctionDefinition
from qrvm.ir_bridge import compile_ir_statements
from qrvm.compiler import QRVMCompiler
from tools.ir_runtime_audit import _bounded_execute


class FunctionIRRoundTripTests(unittest.TestCase):
    def test_function_body_and_default_argument_are_ir(self):
        definition = FunctionDefinition('int', 'increment',
            [FunctionParameter('int', 'value', Integer(41))],
            [ReturnStatement(BinaryOperation(Variable('value'), '+', Integer(1)))])
        lowered = lower_statement(definition)
        self.assertIsInstance(lowered, IRFunctionDefinition)
        self.assertEqual(lowered.parameters[0][2].value, 41)
        self.assertNotIsInstance(lowered.body[0], ReturnStatement)
        statements = [definition, VariableDeclaration('int', 'answer', FunctionCall('increment', [Integer(41)]))]
        direct = QRVMCompiler().compile(statements)
        via_ir = compile_ir_statements(tuple(map(lower_statement, statements)))
        self.assertEqual(direct, via_ir)
        direct_status, direct_result = _bounded_execute(direct)
        ir_status, ir_result = _bounded_execute(via_ir)
        self.assertEqual((direct_status, ir_status), ('ok', 'ok'))
        self.assertEqual(direct_result, ir_result)
        self.assertEqual(ir_result[1]['answer'], 42)


if __name__ == '__main__':
    unittest.main()
