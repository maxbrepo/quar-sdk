"""Chapter 18.10: opt-in debugger observation tests."""
import unittest

from qrvm.debug_hooks import DebugEvent
from qrvm.instructions import OpCode
from qrvm.vm import QRVM


class DebugHookTests(unittest.TestCase):
    def test_disabled_by_default(self):
        vm = QRVM()
        self.assertIsNone(vm.debug_hook)
        vm.run([(OpCode.HALT, None)])

    def test_before_order(self):
        vm, events = QRVM(), []
        vm.set_debug_hook(events.append)
        vm.run([(OpCode.PUSH_INT, 4), (OpCode.HALT, None)])
        self.assertEqual([(e.phase, e.instruction_index) for e in events],
                         [('before', 0), ('before', 1)])

    def test_event_snapshot(self):
        vm, events = QRVM(), []
        vm.set_debug_hook(events.append)
        vm.run([(OpCode.PUSH_INT, 4), (OpCode.HALT, None)])
        self.assertIsInstance(events[0], DebugEvent)
        self.assertEqual(events[0].stack_depth, 0)
        self.assertEqual(events[1].stack_depth, 1)
        with self.assertRaises(AttributeError):
            events[0].phase = 'changed'

    def test_nested_frames(self):
        vm, events = QRVM(), []
        vm.set_debug_hook(events.append)
        vm.run({'instructions': [(OpCode.CALL, ('f', 0)), (OpCode.HALT, None)],
                'functions': {'f': {'parameters': [], 'return_type': 'void',
                                    'instructions': [(OpCode.HALT, None)]}}})
        self.assertIn(('<main>', 'f'), [e.frame_names for e in events])

    def test_error_observation(self):
        vm, events = QRVM(), []
        vm.set_debug_hook(events.append)
        with self.assertRaises(RuntimeError):
            vm.run([(OpCode.LOAD, 'missing')])
        self.assertEqual([e.phase for e in events], ['before', 'error'])
        self.assertEqual(events[-1].opcode, 'LOAD')
        self.assertEqual(events[-1].error_type, 'RuntimeError')
        self.assertIsNotNone(vm.last_diagnostic)

    def test_reset_and_disable(self):
        vm, events = QRVM(), []
        vm.set_debug_hook(events.append)
        vm.run([(OpCode.HALT, None)])
        vm.run([(OpCode.HALT, None)])
        self.assertEqual(len(events), 2)
        vm.set_debug_hook(None)
        vm.run([(OpCode.HALT, None)])
        self.assertEqual(len(events), 2)

    def test_invalid_hook(self):
        with self.assertRaises(TypeError):
            QRVM().set_debug_hook(4)

    def test_callback_error_propagates_and_frames_clean(self):
        vm = QRVM()
        def fail(event):
            raise ValueError('observer failure')
        vm.set_debug_hook(fail)
        with self.assertRaisesRegex(ValueError, 'observer failure'):
            vm.run([(OpCode.HALT, None)])
        self.assertEqual(vm.call_frames, [])
        self.assertIsNone(vm.last_diagnostic)

    def test_no_state_exposure(self):
        vm, events = QRVM(), []
        vm.set_debug_hook(events.append)
        vm.run([(OpCode.PUSH_INT, 3), (OpCode.HALT, None)])
        self.assertFalse(hasattr(events[0], 'locals'))
        self.assertFalse(hasattr(events[0], 'stack'))

    def test_error_hook_failure(self):
        vm = QRVM()
        def fail_on_error(event):
            if event.phase == 'error':
                raise ValueError('observer failure')
        vm.set_debug_hook(fail_on_error)
        with self.assertRaisesRegex(ValueError, 'observer failure'):
            vm.run([(OpCode.LOAD, 'missing')])
        self.assertEqual(vm.call_frames, [])
        self.assertIsNotNone(vm.last_diagnostic)


if __name__ == '__main__':
    unittest.main()
