"""Chapter 18.4: function invocation and operand-stack isolation."""
import unittest
from qrvm.instructions import OpCode as O
from qrvm.vm import QRVM


def fn(params, body, return_type="int"):
    return {"parameters": params, "instructions": body, "return_type": return_type}


class FunctionTests(unittest.TestCase):
    def test_nested_calls(self):
        vm = QRVM()
        vm.run({"instructions": [(O.CALL, ("outer", 0)), (O.HALT, None)], "functions": {
            "outer": fn([], [(O.CALL, ("inner", 0)), (O.RETURN, True)]),
            "inner": fn([], [(O.PUSH_INT, 42), (O.RETURN, True)])}})
        self.assertEqual(vm.stack, [42])

    def test_parameters_and_local_isolation(self):
        vm = QRVM()
        vm.run({"instructions": [(O.PUSH_INT, 9), (O.CALL, ("f", 1)), (O.HALT, None)], "functions": {
            "f": fn(["x"], [(O.LOAD, "x"), (O.RETURN, True)])}})
        self.assertEqual(vm.stack, [9])
        self.assertNotIn("x", vm.variables)

    def test_void_function_discards_temporary_values(self):
        vm = QRVM()
        vm.run({"instructions": [(O.PUSH_INT, 5), (O.CALL, ("f", 0)), (O.HALT, None)], "functions": {
            "f": fn([], [(O.PUSH_INT, 99), (O.RETURN, False)], "void")}})
        self.assertEqual(vm.stack, [5])

    def test_value_function_discards_temporary_values(self):
        vm = QRVM()
        vm.run({"instructions": [(O.PUSH_INT, 5), (O.CALL, ("f", 0)), (O.HALT, None)], "functions": {
            "f": fn([], [(O.PUSH_INT, 99), (O.PUSH_INT, 7), (O.RETURN, True)])}})
        self.assertEqual(vm.stack, [5, 7])

    def test_exception_restores_caller_stack(self):
        vm = QRVM()
        with self.assertRaisesRegex(RuntimeError, "Unknown variable"):
            vm.run({"instructions": [(O.PUSH_INT, 5), (O.CALL, ("f", 0))], "functions": {
                "f": fn([], [(O.PUSH_INT, 9), (O.LOAD, "absent")])}})
        self.assertEqual(vm.stack, [5])
        self.assertEqual(vm.call_frames, [])
        self.assertEqual(vm.last_error_frames, ("<main>", "f"))

    def test_argument_underflow(self):
        vm = QRVM()
        with self.assertRaisesRegex(RuntimeError, "argument stack underflow"):
            vm.run({"instructions": [(O.CALL, ("f", 1))], "functions": {
                "f": fn(["x"], [(O.RETURN, False)], "void")}})
        self.assertEqual(vm.stack, [])

    def test_missing_nonvoid_return(self):
        vm = QRVM()
        with self.assertRaisesRegex(RuntimeError, "did not return"):
            vm.run({"instructions": [(O.CALL, ("f", 0))], "functions": {
                "f": fn([], [(O.PUSH_INT, 7)])}})
        self.assertEqual(vm.stack, [])

    def test_recursive_calls_frames_cleaned(self):
        vm = QRVM()
        with self.assertRaisesRegex(RuntimeError, "Unknown variable"):
            vm.run({"instructions": [(O.CALL, ("f", 0))], "functions": {
                "f": fn([], [(O.LOAD, "missing")])}})
        self.assertEqual(vm.call_frames, [])

    def test_direct_execute_retains_original_stack_semantics(self):
        vm = QRVM()
        vm.execute([(O.PUSH_INT, 8)], {})
        self.assertEqual(vm.stack, [8])
