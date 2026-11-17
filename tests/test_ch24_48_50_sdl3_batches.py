"""SDL3 bounded polling, quit detection, and probe compatibility."""
import json
import unittest
from unittest.mock import Mock
from bindings.sdl3_native_poll import SDL3EventSession
from bindings.sdl3_events import SDL3EventSnapshot
from bindings.sdl3_abi_probe import parse_sdl3_probe
from qrvm.native_abi_contract import NativeABIContractError

class SDL3BatchTests(unittest.TestCase):
    def setUp(self):
        self.session = SDL3EventSession.__new__(SDL3EventSession)
        self.session._active = True
        self.session._poller = Mock()
        self.session.event_ids = {'quit': 256}
        self.session.poll_typed = Mock()

    def test_empty_queue(self):
        self.session.poll_typed.return_value = None
        self.assertEqual(self.session.poll_batch(), [])

    def test_drains_until_empty(self):
        events = [SDL3EventSnapshot(i, b'') for i in range(3)]
        self.session.poll_typed.side_effect = [*events, None]
        self.assertEqual(self.session.poll_batch(), events)
        self.assertEqual(self.session.poll_typed.call_count, 4)

    def test_batch_limit(self):
        self.session.poll_typed.return_value = SDL3EventSnapshot(7, b'')
        self.assertEqual(len(self.session.poll_batch(3)), 3)
        self.assertEqual(self.session.poll_typed.call_count, 3)

    def test_invalid_limits(self):
        for value in (0, -1, 4097, True, 1.2, '3'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.session.poll_batch(value)

    def test_closed_session(self):
        self.session._active = False
        with self.assertRaises(NativeABIContractError):
            self.session.poll_batch()

    def test_quit_event(self):
        self.assertTrue(self.session.is_quit_event(SDL3EventSnapshot(256, b'')))
        self.assertFalse(self.session.is_quit_event(SDL3EventSnapshot(257, b'')))
        self.assertFalse(self.session.is_quit_event(None))

    def test_missing_quit_id(self):
        self.session.event_ids = {}
        with self.assertRaises(NativeABIContractError):
            self.session.is_quit_event(SDL3EventSnapshot(256, b''))

    def test_probe_accepts_legacy_and_quit_contracts(self):
        sample = {'size': 64, 'alignment': 8,
                  'offsets': {'type': 0, 'key_scancode': 16, 'key_key': 20,
                              'motion_x': 24, 'motion_y': 28},
                  'event_ids': {'keydown': 10, 'keyup': 11, 'motion': 12}}
        _, ids = parse_sdl3_probe(json.dumps(sample))
        self.assertNotIn('quit', ids)
        sample['event_ids']['quit'] = 13
        _, ids = parse_sdl3_probe(json.dumps(sample))
        self.assertEqual(ids['quit'], 13)

    def test_probe_rejects_duplicate_quit_id(self):
        sample = {'size': 64, 'alignment': 8,
                  'offsets': {'type': 0, 'key_scancode': 16, 'key_key': 20,
                              'motion_x': 24, 'motion_y': 28},
                  'event_ids': {'keydown': 10, 'keyup': 11, 'motion': 12, 'quit': 10}}
        with self.assertRaises(NativeABIContractError):
            parse_sdl3_probe(json.dumps(sample))

if __name__ == '__main__':
    unittest.main()
