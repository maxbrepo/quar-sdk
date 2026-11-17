"""Real SDL3 queue smoke test; skips when development libraries are absent."""
from __future__ import annotations

import ctypes
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from bindings.sdl3_native_poll import SDL3EventSession, compile_sdl3_poll_shim


class SDL3RealQueueSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if shutil.which('pkg-config') is None or shutil.which('cc') is None:
            raise unittest.SkipTest('C compiler or pkg-config unavailable')
        if subprocess.run(['pkg-config', '--exists', 'sdl3'], check=False).returncode:
            raise unittest.SkipTest('SDL3 development files unavailable')
        cls._tmp = tempfile.TemporaryDirectory(prefix='vq_sdl3_smoke_')
        try:
            cls.library = compile_sdl3_poll_shim(Path(cls._tmp.name) / 'libvq_sdl3_smoke.so')
        except (subprocess.CalledProcessError, OSError):
            cls._tmp.cleanup()
            raise

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, '_tmp'):
            cls._tmp.cleanup()

    def test_native_quit_event_reaches_session(self):
        with SDL3EventSession(self.library) as session:
            # Empty any pending events so the test has a deterministic queue.
            session.poll_batch(4096)
            native = ctypes.CDLL(str(self.library))
            native.vq_sdl3_test_push_quit.argtypes = []
            native.vq_sdl3_test_push_quit.restype = ctypes.c_int32
            self.assertEqual(native.vq_sdl3_test_push_quit(), 1)
            received = []
            count, should_quit = session.dispatch_frame(received.append)
            self.assertTrue(should_quit)
            self.assertGreaterEqual(count, 1)
            self.assertTrue(session.is_quit_event(received[-1]))

    def test_session_closes_after_context(self):
        session = SDL3EventSession(self.library)
        with session:
            self.assertTrue(session._active)
        self.assertFalse(session._active)
        with self.assertRaises(Exception):
            session.poll()

    def test_repeated_open_close(self):
        for _ in range(3):
            with SDL3EventSession(self.library) as session:
                self.assertTrue(session._active)
                session.poll_batch(4096)


if __name__ == '__main__':
    unittest.main()
