"""Chapter 4.53: typed inter-function QIR call contract, without code emission."""
import unittest
from frontend.quar.qir.model import QBlock, QFunction, QInstruction, QModule, QReturn, QType, QValue
from frontend.quar.qir.validation import QIRValidationError, validate_module
from frontend.quar.qir.backend_readiness import inspect_backend_readiness

I32 = QType('i32')

def module_with_call(callee='helper', arg_type=I32, result_type=I32, parameters=(I32,)):
    args = tuple(QValue(f'a{i}', kind) for i, kind in enumerate(parameters))
    helper = QFunction('helper', I32, args, (QBlock('entry', (), QReturn(args[0] if args else None)),))
    arg = QValue('input', arg_type)
    output = QValue('output', result_type)
    caller = QFunction('caller', result_type, (arg,), (QBlock('entry',
        (QInstruction('call', (arg,), output, immediate=callee),), QReturn(output)),))
    return QModule('calls', (helper, caller))

class CallContractTests(unittest.TestCase):
    def test_valid_call_between_functions(self):
        validate_module(module_with_call())

    def test_unknown_function_rejected(self):
        with self.assertRaisesRegex(QIRValidationError, 'Unknown'):
            validate_module(module_with_call(callee='missing'))

    def test_argument_width_rejected(self):
        with self.assertRaisesRegex(QIRValidationError, 'argument mismatch'):
            validate_module(module_with_call(arg_type=QType('i16')))

    def test_result_width_rejected(self):
        with self.assertRaisesRegex(QIRValidationError, 'result mismatch'):
            validate_module(module_with_call(result_type=QType('i16')))

    def test_call_still_not_ready_for_c_adapter(self):
        module = module_with_call()
        validate_module(module)
        report = inspect_backend_readiness(module.functions[1], 'c')
        self.assertFalse(report.ready_for_adapter)
        self.assertTrue(any(issue.feature == 'opcode' for issue in report.issues))

    def test_malformed_symbol_rejected(self):
        with self.assertRaises(QIRValidationError):
            validate_module(module_with_call(callee='bad-name'))

if __name__ == '__main__':
    unittest.main()
