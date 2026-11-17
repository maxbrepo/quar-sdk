"""Chapter 5.20: first executable, non-capturing function references."""
import unittest
from frontend.quar.ast_nodes import FunctionReference, IndirectFunctionCall, Variable, Integer
from qrvm.compiler import QRVMCompiler
from qrvm.instructions import OpCode
from qrvm.vm import QRVM


class IndirectCallTests(unittest.TestCase):
    def setUp(self):
        self.compiler = QRVMCompiler()
        self.vm = QRVM()
        self.vm.functions = {
            'identity': {
                'parameters': ['x'],
                'return_type': 'int',
                'instructions': [(OpCode.LOAD, 'x'), (OpCode.RETURN, True)],
            }
        }

    def test_reference_and_indirect_call(self):
        instructions = self.compiler.compile_expression(
            IndirectFunctionCall(FunctionReference('identity'), [Integer(42)])
        )
        self.vm.execute(instructions, {})
        self.assertEqual(self.vm.stack.pop(), 42)

    def test_reference_stored_in_variable(self):
        instructions = [(OpCode.FUNCTION_REF, 'identity'), (OpCode.STORE, 'callback')]
        instructions += self.compiler.compile_expression(
            IndirectFunctionCall(Variable('callback'), [Integer(7)])
        )
        self.vm.execute(instructions, {})
        self.assertEqual(self.vm.stack.pop(), 7)

    def test_invalid_target_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'not a function reference'):
            self.vm.execute([(OpCode.PUSH_INT, 4), (OpCode.CALL_INDIRECT, 0)], {})

    def test_argument_count_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'argument count mismatch'):
            self.vm.execute([(OpCode.FUNCTION_REF, 'identity'), (OpCode.CALL_INDIRECT, 0)], {})

    def test_missing_reference_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'Unknown function reference'):
            self.vm.execute([(OpCode.FUNCTION_REF, 'missing')], {})


if __name__ == '__main__':
    unittest.main()
