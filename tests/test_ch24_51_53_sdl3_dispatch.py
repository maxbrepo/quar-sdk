"""Bounded event dispatch contract for QGF, without requiring SDL3 at test time."""
import unittest
from unittest.mock import Mock
from bindings.sdl3_native_poll import SDL3EventSession
from bindings.sdl3_events import SDL3EventSnapshot
from qrvm.native_abi_contract import NativeABIContractError


class SDL3DispatchTests(unittest.TestCase):
    def setUp(self):
        self.session = SDL3EventSession.__new__(SDL3EventSession)
        self.session._active = True
        self.session._poller = Mock()
        self.session.event_ids = {'quit': 256}
        self.session.poll_typed = Mock()

    def test_empty_queue(self):
        self.session.poll_typed.return_value = None
        received = []
        self.assertEqual(self.session.dispatch_events(received.append), (0, False))
        self.assertEqual(received, [])

    def test_multiple_events(self):
        events = [SDL3EventSnapshot(2, b'a'), SDL3EventSnapshot(3, b'b')]
        self.session.poll_typed.side_effect = [*events, None]
        received = []
        self.assertEqual(self.session.dispatch_events(received.append), (2, False))
        self.assertEqual(received, events)

    def test_quit_stops_immediately(self):
        events = [SDL3EventSnapshot(2, b''), SDL3EventSnapshot(256, b''), SDL3EventSnapshot(3, b'')]
        self.session.poll_typed.side_effect = events
        received = []
        self.assertEqual(self.session.dispatch_events(received.append), (2, True))
        self.assertEqual(received, events[:2])
        self.assertEqual(self.session.poll_typed.call_count, 2)

    def test_bounded_dispatch(self):
        self.session.poll_typed.return_value = SDL3EventSnapshot(3, b'')
        self.assertEqual(self.session.dispatch_events(lambda _: None, 5), (5, False))
        self.assertEqual(self.session.poll_typed.call_count, 5)

    def test_invalid_limits(self):
        for value in (0, -1, 4097, True, 1.5, '4'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.session.dispatch_events(lambda _: None, value)

    def test_closed_session(self):
        self.session._active = False
        with self.assertRaises(NativeABIContractError):
            self.session.dispatch_events(lambda _: None)

    def test_callback_exception_propagates(self):
        self.session.poll_typed.return_value = SDL3EventSnapshot(3, b'')
        def fail(_event):
            raise RuntimeError('callback failed')
        with self.assertRaisesRegex(RuntimeError, 'callback failed'):
            self.session.dispatch_events(fail)
        self.assertEqual(self.session.poll_typed.call_count, 1)

    def test_non_callable_callback(self):
        with self.assertRaises(TypeError):
            self.session.dispatch_events(None)

    def test_missing_quit_contract(self):
        self.session.event_ids = {}
        self.session.poll_typed.return_value = SDL3EventSnapshot(3, b'')
        with self.assertRaises(NativeABIContractError):
            self.session.dispatch_events(lambda _: None)


if __name__ == '__main__':
    unittest.main()
