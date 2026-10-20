"""Chapter 18.3: execution context bookkeeping regression tests."""
import unittest
from qrvm.call_frames import CallFrame, describe_frames
from qrvm.instructions import OpCode
from qrvm.vm import QRVM


class CallFrameTests(unittest.TestCase):
    def test_empty_after_main(self):
        vm = QRVM()
        vm.run([(OpCode.PUSH_INT, 3), (OpCode.HALT, None)])
        self.assertEqual(vm.stack, [3])
        self.assertEqual(vm.call_frames, [])

    def test_function_call_preserves_result(self):
        vm = QRVM()
        vm.run({"instructions": [(OpCode.CALL, ("f", 0)), (OpCode.HALT, None)],
                "functions": {"f": {"parameters": [], "return_type": "int",
                                    "instructions": [(OpCode.PUSH_INT, 7), (OpCode.RETURN, True)]}}})
        self.assertEqual(vm.stack, [7])
        self.assertEqual(vm.call_frames, [])

    def test_nested_failure_trace(self):
        vm = QRVM()
        program = {"instructions": [(OpCode.CALL, ("outer", 0))], "functions": {
            "outer": {"parameters": [], "return_type": "int", "instructions": [(OpCode.CALL, ("inner", 0)), (OpCode.RETURN, True)]},
            "inner": {"parameters": [], "return_type": "int", "instructions": [(OpCode.LOAD, "missing"), (OpCode.RETURN, True)]}}}
        with self.assertRaisesRegex(RuntimeError, "Unknown variable"):
            vm.run(program)
        self.assertEqual(vm.last_error_frames, ("<main>", "outer", "inner"))
        self.assertEqual(vm.call_frames, [])

    def test_scoped_frame_and_cleanup(self):
        vm = QRVM()
        with self.assertRaisesRegex(RuntimeError, "Unknown variable"):
            vm.execute([(OpCode.LOAD, "absent")], {}, scoped=True)
        self.assertEqual(vm.last_error_frames, ("<scope>",))
        self.assertEqual(vm.call_frames, [])

    def test_run_resets_old_trace(self):
        vm = QRVM()
        with self.assertRaises(RuntimeError):
            vm.run([(OpCode.LOAD, "x")])
        vm.run([(OpCode.HALT, None)])
        self.assertEqual(vm.last_error_frames, ())

    def test_live_locals_reference(self):
        values = {"x": 1}
        frame = CallFrame("f", values, 2)
        values["x"] = 4
        self.assertEqual(frame.locals["x"], 4)

    def test_frame_trace_immutable(self):
        self.assertEqual(describe_frames([CallFrame("a", {}, 0), CallFrame("b", {}, 1)]), ("a", "b"))

    def test_existing_direct_execute_works(self):
        vm = QRVM()
        values = {}
        vm.execute([(OpCode.PUSH_INT, 8), (OpCode.STORE, "x")], values)
        self.assertEqual(values, {"x": 8})
        self.assertEqual(vm.call_frames, [])
