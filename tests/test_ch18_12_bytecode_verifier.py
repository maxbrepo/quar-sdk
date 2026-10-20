"""Chapter 18.12: opt-in QRVM bytecode verification."""
import unittest

from qrvm.bytecode_format import wrap_legacy_program
from qrvm.bytecode_loader import BytecodeLoadError, load_bytecode, run_loaded_bytecode
from qrvm.bytecode_verifier import BytecodeVerificationError, verify_bytecode
from qrvm.instructions import OpCode as O
from qrvm.vm import QRVM


class VerifierTests(unittest.TestCase):
    def check(self, code):
        return verify_bytecode(wrap_legacy_program(code))

    def test_valid_linear(self):
        report = self.check([(O.PUSH_INT, 2), (O.PUSH_INT, 3), (O.ADD, None), (O.HALT, None)])
        self.assertEqual((report.bodies, report.instructions, report.stack_checked_bodies), (1, 4, 1))

    def test_valid_conditional(self):
        self.check([(O.PUSH_BOOL, True), (O.JUMP_IF_FALSE, 4),
                    (O.PUSH_INT, 3), (O.POP, None), (O.HALT, None)])

    def test_valid_loop(self):
        self.check([(O.PUSH_BOOL, False), (O.JUMP_IF_FALSE, 4),
                    (O.PUSH_INT, 1), (O.JUMP, 0), (O.HALT, None)])

    def test_invalid_jump_bool(self):
        with self.assertRaisesRegex(BytecodeVerificationError, 'jump target'):
            self.check([(O.JUMP, True)])

    def test_invalid_jump_range(self):
        with self.assertRaisesRegex(BytecodeVerificationError, 'jump target'):
            self.check([(O.JUMP, 2)])

    def test_stack_underflow(self):
        with self.assertRaisesRegex(BytecodeVerificationError, 'stack underflow'):
            self.check([(O.ADD, None)])

    def test_branch_underflow(self):
        with self.assertRaisesRegex(BytecodeVerificationError, 'stack underflow'):
            self.check([(O.PUSH_BOOL, True), (O.JUMP_IF_FALSE, 4),
                        (O.PUSH_INT, 3), (O.JUMP, 4), (O.POP, None)])

    def test_invalid_call_metadata(self):
        with self.assertRaisesRegex(BytecodeVerificationError, 'call metadata'):
            self.check([(O.CALL, ('f', -1))])

    def test_unknown_stack_effect_is_inconclusive(self):
        report = self.check([(O.CALL, ('f', 0)), (O.HALT, None)])
        self.assertEqual(report.stack_checked_bodies, 0)

    def test_function_body_checked(self):
        package = wrap_legacy_program({'instructions': [(O.HALT, None)],
            'functions': {'f': {'parameters': [], 'return_type': 'void',
                               'instructions': [(O.POP, None)]}}})
        with self.assertRaisesRegex(BytecodeVerificationError, 'functions'):
            verify_bytecode(package)

    def test_loader_opt_in_rejects(self):
        with self.assertRaises(BytecodeLoadError):
            load_bytecode([(O.ADD, None)], allow_legacy=True, verify=True)
        self.assertIsNotNone(load_bytecode([(O.ADD, None)], allow_legacy=True))

    def test_loader_verified_executes(self):
        loaded = load_bytecode([(O.PUSH_INT, 7), (O.HALT, None)],
                               allow_legacy=True, verify=True)
        vm = QRVM()
        run_loaded_bytecode(vm, loaded)
        self.assertEqual(vm.stack, [7])


if __name__ == '__main__':
    unittest.main()
