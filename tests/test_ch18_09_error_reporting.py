"""Chapter 18.9: structured runtime errors preserve existing exception behavior."""
import unittest

from qrvm.error_reporting import QVMDiagnostic
from qrvm.instructions import OpCode
from qrvm.vm import QRVM


class ErrorReportingTests(unittest.TestCase):
    def test_missing_variable(self):
        vm = QRVM()
        with self.assertRaisesRegex(RuntimeError, 'Unknown variable'):
            vm.run([(OpCode.PUSH_INT, 2), (OpCode.LOAD, 'absent')])
        d = vm.last_diagnostic
        self.assertIsInstance(d, QVMDiagnostic)
        self.assertEqual(d.instruction_index, 1)
        self.assertEqual(d.opcode, 'LOAD')
        self.assertEqual(d.frame_names, ('<main>',))

    def test_nested_deepest_instruction(self):
        vm = QRVM()
        program = {'instructions': [(OpCode.CALL, ('f', 0))], 'functions': {
            'f': {'parameters': [], 'return_type': 'int', 'instructions': [
                (OpCode.PUSH_INT, 1), (OpCode.LOAD, 'absent')]}}}
        with self.assertRaises(RuntimeError):
            vm.run(program)
        self.assertEqual(vm.last_diagnostic.frame_names, ('<main>', 'f'))
        self.assertEqual(vm.last_diagnostic.instruction_index, 1)
        self.assertEqual(vm.last_diagnostic.opcode, 'LOAD')
        self.assertEqual(vm.call_frames, [])

    def test_reset_on_next_run(self):
        vm = QRVM()
        with self.assertRaises(RuntimeError):
            vm.run([(OpCode.LOAD, 'x')])
        vm.run([(OpCode.HALT, None)])
        self.assertIsNone(vm.last_diagnostic)

    def test_success_has_no_diagnostic(self):
        vm = QRVM()
        vm.run([(OpCode.PUSH_INT, 2), (OpCode.HALT, None)])
        self.assertIsNone(vm.last_diagnostic)

    def test_direct_execute(self):
        vm = QRVM()
        with self.assertRaises(RuntimeError):
            vm.execute([(OpCode.LOAD, 'x')], {})
        self.assertEqual(vm.last_diagnostic.frame_names, ('<execute>',))

    def test_format(self):
        d = QVMDiagnostic('RuntimeError', 'bad', ('<main>', 'f'), 3, 'LOAD')
        self.assertIn('<main> -> f, instruction 3 (LOAD)', d.format())

    def test_unknown_opcode(self):
        vm = QRVM()
        with self.assertRaisesRegex(RuntimeError, 'Unknown opcode'):
            vm.run([('MISSING_OPCODE', None)])
        self.assertEqual(vm.last_diagnostic.opcode, 'MISSING_OPCODE')

    def test_diagnostic_immutable(self):
        d = QVMDiagnostic('RuntimeError', 'bad', ('main',), 0, 'LOAD')
        with self.assertRaises(AttributeError):
            d.message = 'changed'
