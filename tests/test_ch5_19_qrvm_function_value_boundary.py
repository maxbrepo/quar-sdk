"""Chapter 5.19 boundary upgraded by the Chapter 5.20 runtime bridge."""
import unittest
from frontend.quar.ast_nodes import FunctionReference, IndirectFunctionCall, Variable
from qrvm.compiler import QRVMCompiler
from qrvm.instructions import OpCode


class FunctionValueBoundaryTests(unittest.TestCase):
    def test_reference_emits_handle(self):
        self.assertEqual(QRVMCompiler().compile_expression(FunctionReference('sum')),
                         [(OpCode.FUNCTION_REF, 'sum')])

    def test_indirect_call_emits_opcode(self):
        code = QRVMCompiler().compile_expression(IndirectFunctionCall(Variable('callback'), []))
        self.assertEqual(code, [(OpCode.LOAD, 'callback'), (OpCode.CALL_INDIRECT, 0)])


if __name__ == '__main__':
    unittest.main()
