"""Native SDL3 typed-event roundtrip through QRVM's existing FFI path."""
from __future__ import annotations

import ctypes
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from bindings.sdl3_events import SDL3KeyboardSnapshot, SDL3MouseMotionSnapshot
from bindings.sdl3_native_poll import SDL3EventSession, compile_sdl3_poll_shim


class SDL3TypedNativeQueueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('pkg-config') or not shutil.which('cc'):
            raise unittest.SkipTest('C compiler or pkg-config unavailable')
        if subprocess.run(['pkg-config', '--exists', 'sdl3'], check=False).returncode:
            raise unittest.SkipTest('SDL3 development files unavailable')
        cls._temporary = tempfile.TemporaryDirectory(prefix='vq_sdl3_typed_')
        try:
            cls.path = compile_sdl3_poll_shim(Path(cls._temporary.name) / 'libvq_sdl3_typed.so')
            cls.native = ctypes.CDLL(str(cls.path))
            cls.native.vq_sdl3_test_push_key.argtypes = [ctypes.c_int32] * 3
            cls.native.vq_sdl3_test_push_key.restype = ctypes.c_int32
            cls.native.vq_sdl3_test_push_motion.argtypes = [ctypes.c_float] * 2
            cls.native.vq_sdl3_test_push_motion.restype = ctypes.c_int32
        except BaseException:
            cls._temporary.cleanup()
            raise

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, '_temporary'):
            cls._temporary.cleanup()

    def test_key_down_roundtrip(self):
        with SDL3EventSession(self.path) as session:
            session.poll_batch(4096)
            self.assertEqual(self.native.vq_sdl3_test_push_key(1, 4, 97), 1)
            events = session.poll_batch(16)
            keys = [event for event in events if isinstance(event, SDL3KeyboardSnapshot)]
            self.assertEqual(len(keys), 1)
            self.assertEqual((keys[0].scancode, keys[0].keycode), (4, 97))
            self.assertEqual(keys[0].type, session.event_ids['keydown'])

    def test_key_up_roundtrip(self):
        with SDL3EventSession(self.path) as session:
            session.poll_batch(4096)
            self.assertEqual(self.native.vq_sdl3_test_push_key(0, 4, 97), 1)
            keys = [event for event in session.poll_batch(16) if isinstance(event, SDL3KeyboardSnapshot)]
            self.assertEqual(len(keys), 1)
            self.assertEqual(keys[0].type, session.event_ids['keyup'])

    def test_mouse_motion_roundtrip(self):
        with SDL3EventSession(self.path) as session:
            session.poll_batch(4096)
            self.assertEqual(self.native.vq_sdl3_test_push_motion(12.5, -7.25), 1)
            motions = [event for event in session.poll_batch(16) if isinstance(event, SDL3MouseMotionSnapshot)]
            self.assertEqual(len(motions), 1)
            self.assertAlmostEqual(motions[0].x, 12.5)
            self.assertAlmostEqual(motions[0].y, -7.25)


if __name__ == '__main__':
    unittest.main()
