"""Chapter 24: bounded event dispatch, error propagation and native queue integration."""
from __future__ import annotations

import ctypes
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from bindings.sdl3_events import SDL3EventSnapshot, SDL3KeyboardSnapshot, SDL3MouseMotionSnapshot
from bindings.sdl3_native_poll import SDL3EventSession, compile_sdl3_poll_shim


class DispatchContractTests(unittest.TestCase):
    def session(self, events):
        session = object.__new__(SDL3EventSession)
        session._active = True
        session._poller = object()
        session.event_ids = {'quit': 256}
        iterator = iter(events)
        session.poll_typed = lambda: next(iterator, None)
        return session

    def test_quit_stops_dispatch_without_consuming_later_events(self):
        first = SDL3EventSnapshot(1, b'a')
        quit_event = SDL3EventSnapshot(256, b'b')
        later = SDL3EventSnapshot(2, b'c')
        session = self.session([first, quit_event, later])
        seen = []
        self.assertEqual(session.dispatch_frame(seen.append, 8), (2, True))
        self.assertEqual(seen, [first, quit_event])
        self.assertEqual(session.poll_typed(), later)

    def test_event_limit_is_respected(self):
        session = self.session([SDL3EventSnapshot(n, b'') for n in range(5)])
        seen = []
        self.assertEqual(session.dispatch_frame(seen.append, 2), (2, False))
        self.assertEqual(len(seen), 2)
        self.assertEqual(session.poll_typed().type, 2)

    def test_callback_exception_propagates_and_stops_polling(self):
        session = self.session([SDL3EventSnapshot(1, b''), SDL3EventSnapshot(2, b'')])
        def fail(_event):
            raise RuntimeError('QGF callback failed')
        with self.assertRaisesRegex(RuntimeError, 'QGF callback failed'):
            session.dispatch_frame(fail, 2)
        self.assertEqual(session.poll_typed().type, 2)

    def test_invalid_dispatch_limit_rejected(self):
        session = self.session([])
        for invalid in (0, -1, 4097, True, 1.5, '3'):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                session.dispatch_frame(lambda _: None, invalid)

    def test_closed_session_rejects_dispatch(self):
        session = self.session([])
        session._active = False
        with self.assertRaises(Exception):
            session.dispatch_frame(lambda _: None)


class SDL3NativeDispatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('cc') or not shutil.which('pkg-config'):
            raise unittest.SkipTest('C compiler or pkg-config unavailable')
        if subprocess.run(['pkg-config', '--exists', 'sdl3'], check=False).returncode:
            raise unittest.SkipTest('SDL3 development headers unavailable')
        cls.tmp = tempfile.TemporaryDirectory(prefix='vq_ch24_65_68_')
        try:
            cls.path = compile_sdl3_poll_shim(Path(cls.tmp.name) / 'libvq_sdl3_dispatch.so')
            cls.native = ctypes.CDLL(str(cls.path))
            cls.native.vq_sdl3_test_push_quit.argtypes = []
            cls.native.vq_sdl3_test_push_quit.restype = ctypes.c_int32
            cls.native.vq_sdl3_test_push_key.argtypes = [ctypes.c_int32] * 3
            cls.native.vq_sdl3_test_push_key.restype = ctypes.c_int32
            cls.native.vq_sdl3_test_push_motion.argtypes = [ctypes.c_float] * 2
            cls.native.vq_sdl3_test_push_motion.restype = ctypes.c_int32
        except BaseException:
            cls.tmp.cleanup()
            raise

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'tmp'):
            cls.tmp.cleanup()

    def test_native_typed_sequence_and_quit(self):
        with SDL3EventSession(self.path) as session:
            session.poll_batch(4096)
            self.assertEqual(self.native.vq_sdl3_test_push_key(1, 4, 97), 1)
            self.assertEqual(self.native.vq_sdl3_test_push_motion(12.5, -7.25), 1)
            self.assertEqual(self.native.vq_sdl3_test_push_quit(), 1)
            seen = []
            count, quit_requested = session.dispatch_frame(seen.append, 16)
            self.assertEqual((count, quit_requested), (3, True))
            self.assertIsInstance(seen[0], SDL3KeyboardSnapshot)
            self.assertIsInstance(seen[1], SDL3MouseMotionSnapshot)
            self.assertEqual(seen[2].type, session.event_ids['quit'])
            self.assertEqual((seen[0].scancode, seen[0].keycode), (4, 97))
            self.assertAlmostEqual(seen[1].x, 12.5)
            self.assertAlmostEqual(seen[1].y, -7.25)

    def test_native_session_closes_after_exception(self):
        session = SDL3EventSession(self.path)
        with self.assertRaisesRegex(RuntimeError, 'handler error'):
            with session:
                session.poll_batch(4096)
                self.assertEqual(self.native.vq_sdl3_test_push_quit(), 1)
                def fail(_event):
                    raise RuntimeError('handler error')
                session.dispatch_frame(fail)
        self.assertFalse(session._active)
        with self.assertRaises(Exception):
            session.poll()


if __name__ == '__main__':
    unittest.main()
