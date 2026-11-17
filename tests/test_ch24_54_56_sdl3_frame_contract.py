"""Frame-level SDL3 event contract; does not require SDL3 to be installed."""
import unittest
from unittest.mock import Mock

from bindings.sdl3_events import SDL3EventSnapshot
from bindings.sdl3_native_poll import SDL3EventSession
from qrvm.native_abi_contract import NativeABIContractError


class SDL3FrameContractTests(unittest.TestCase):
    def setUp(self):
        self.session = SDL3EventSession.__new__(SDL3EventSession)
        self.session._active = True
        self.session._poller = Mock()
        self.session.event_ids = {'quit': 256}
        self.session.poll_typed = Mock()

    def test_empty_frame(self):
        self.session.poll_typed.return_value = None
        self.assertEqual(self.session.dispatch_frame(lambda _: None), (0, False))

    def test_event_order_and_frame_limit(self):
        self.session.poll_typed.side_effect = [SDL3EventSnapshot(n, b'') for n in range(1, 5)]
        received = []
        self.assertEqual(self.session.dispatch_frame(received.append, 3), (3, False))
        self.assertEqual([event.type for event in received], [1, 2, 3])
        self.assertEqual(self.session.poll_typed.call_count, 3)

    def test_quit_stops_frame(self):
        self.session.poll_typed.side_effect = [SDL3EventSnapshot(2, b''), SDL3EventSnapshot(256, b'')]
        received = []
        self.assertEqual(self.session.dispatch_frame(received.append), (2, True))
        self.assertEqual([event.type for event in received], [2, 256])

    def test_callback_failure_propagates(self):
        self.session.poll_typed.return_value = SDL3EventSnapshot(2, b'')
        with self.assertRaisesRegex(RuntimeError, 'handler'):
            self.session.dispatch_frame(lambda _: (_ for _ in ()).throw(RuntimeError('handler')))
        self.assertEqual(self.session.poll_typed.call_count, 1)

    def test_inactive_session_rejected(self):
        self.session._active = False
        with self.assertRaises(NativeABIContractError):
            self.session.dispatch_frame(lambda _: None)

    def test_invalid_event_budget(self):
        for value in (0, -1, 4097, True, 2.5):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.session.dispatch_frame(lambda _: None, value)

    def test_callback_must_be_callable(self):
        with self.assertRaises(TypeError):
            self.session.dispatch_frame(None)

    def test_missing_quit_contract(self):
        self.session.event_ids = {}
        self.session.poll_typed.return_value = SDL3EventSnapshot(2, b'')
        with self.assertRaises(NativeABIContractError):
            self.session.dispatch_frame(lambda _: None)


if __name__ == '__main__':
    unittest.main()
