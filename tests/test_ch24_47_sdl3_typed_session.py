"""Typed SDL3 session dispatch without requiring SDL3 on the test host."""
import struct
import unittest
from unittest.mock import Mock

from bindings.sdl3_events import SDL3EventSnapshot, SDL3KeyboardSnapshot, SDL3MouseMotionSnapshot
from bindings.sdl3_native_poll import SDL3EventSession
from qrvm.native_abi_contract import NativeABIContractError, NativeOutputABIContract


class TypedSessionTests(unittest.TestCase):
    def setUp(self):
        self.session = SDL3EventSession.__new__(SDL3EventSession)
        self.session._active = True
        self.session.event_ids = {'keydown': 10, 'keyup': 11, 'motion': 12}
        self.contract = NativeOutputABIContract(
            size=32, alignment=4,
            offsets=(('type', 0), ('key_scancode', 4), ('key_key', 8),
                     ('motion_x', 12), ('motion_y', 16)),
        )
        self.session._poller = Mock()
        self.session._poller.contract = self.contract

    def event(self, event_type):
        raw = bytearray(32)
        struct.pack_into('=I', raw, 0, event_type)
        struct.pack_into('=I', raw, 4, 33)
        struct.pack_into('=I', raw, 8, 99)
        struct.pack_into('=f', raw, 12, 1.5)
        struct.pack_into('=f', raw, 16, -2.25)
        return SDL3EventSnapshot(event_type, bytes(raw))

    def test_empty_queue(self):
        self.session._poller.poll.return_value = None
        self.assertIsNone(self.session.poll_typed())

    def test_keydown(self):
        self.session._poller.poll.return_value = self.event(10)
        result = self.session.poll_typed()
        self.assertIsInstance(result, SDL3KeyboardSnapshot)
        self.assertEqual((result.scancode, result.keycode), (33, 99))

    def test_keyup(self):
        self.session._poller.poll.return_value = self.event(11)
        self.assertIsInstance(self.session.poll_typed(), SDL3KeyboardSnapshot)

    def test_motion(self):
        self.session._poller.poll.return_value = self.event(12)
        result = self.session.poll_typed()
        self.assertIsInstance(result, SDL3MouseMotionSnapshot)
        self.assertAlmostEqual(result.x, 1.5)
        self.assertAlmostEqual(result.y, -2.25)

    def test_unknown_preserved(self):
        event = self.event(99)
        self.session._poller.poll.return_value = event
        self.assertIs(self.session.poll_typed(), event)

    def test_inactive_rejected(self):
        self.session._active = False
        with self.assertRaises(NativeABIContractError):
            self.session.poll_typed()


if __name__ == '__main__':
    unittest.main()
