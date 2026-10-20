"""Chapter 18.11: optional QVM instruction profiling."""
import unittest
from qrvm.instructions import OpCode
from qrvm.vm import QRVM


class ProfilingTests(unittest.TestCase):
    def test_off_by_default(self):
        vm = QRVM()
        vm.run([(OpCode.HALT, None)])
        self.assertIsNone(vm.profile_snapshot())

    def test_counts_and_names(self):
        vm = QRVM()
        vm.set_profiling(True)
        vm.run([(OpCode.PUSH_INT, 1), (OpCode.PUSH_INT, 2),
                (OpCode.ADD, None), (OpCode.HALT, None)])
        snap = vm.profile_snapshot()
        self.assertEqual(snap.total.instructions, 4)
        self.assertEqual(snap.by_opcode['PUSH_INT'].instructions, 2)
        self.assertEqual(snap.by_function['<main>'].instructions, 4)

    def test_nested_functions(self):
        vm = QRVM()
        vm.set_profiling(True)
        vm.run({'instructions': [(OpCode.CALL, ('f', 0)), (OpCode.HALT, None)],
                'functions': {'f': {'parameters': [], 'return_type': 'void',
                                    'instructions': [(OpCode.HALT, None)]}}})
        snap = vm.profile_snapshot()
        self.assertEqual(snap.total.instructions, 3)
        self.assertEqual(snap.by_function['f'].instructions, 1)
        self.assertEqual(snap.by_function['<main>'].instructions, 2)

    def test_reset_between_runs(self):
        vm = QRVM()
        vm.set_profiling(True)
        vm.run([(OpCode.HALT, None)])
        vm.run([(OpCode.PUSH_INT, 1), (OpCode.HALT, None)])
        self.assertEqual(vm.profile_snapshot().total.instructions, 2)

    def test_disable(self):
        vm = QRVM()
        vm.set_profiling(True)
        vm.set_profiling(False)
        self.assertIsNone(vm.profile_snapshot())

    def test_invalid_flag(self):
        with self.assertRaises(TypeError):
            QRVM().set_profiling(1)

    def test_error_is_counted(self):
        vm = QRVM()
        vm.set_profiling(True)
        with self.assertRaises(RuntimeError):
            vm.run([(OpCode.LOAD, 'unknown')])
        self.assertEqual(vm.profile_snapshot().by_opcode['LOAD'].instructions, 1)
        self.assertIsNotNone(vm.last_diagnostic)

    def test_snapshot_detached(self):
        vm = QRVM()
        vm.set_profiling(True)
        vm.run([(OpCode.HALT, None)])
        snap = vm.profile_snapshot()
        vm.run([(OpCode.PUSH_INT, 1), (OpCode.HALT, None)])
        self.assertEqual(snap.total.instructions, 1)
        with self.assertRaises(AttributeError):
            snap.total.instructions = 10

    def test_timings_nonnegative(self):
        vm = QRVM()
        vm.set_profiling(True)
        vm.run([(OpCode.HALT, None)])
        self.assertGreaterEqual(vm.profile_snapshot().total.elapsed_ns, 0)

    def test_debug_hook_compatibility(self):
        vm, events = QRVM(), []
        vm.set_profiling(True)
        vm.set_debug_hook(events.append)
        vm.run([(OpCode.HALT, None)])
        self.assertEqual(len(events), 1)
        self.assertEqual(vm.profile_snapshot().total.instructions, 1)


if __name__ == '__main__':
    unittest.main()
