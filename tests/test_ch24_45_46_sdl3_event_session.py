"""SDL3 event-session lifecycle, failure cleanup, and optional real SDL3."""
import ctypes
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from bindings.sdl3_native_poll import SDL3EventSession, compile_sdl3_poll_shim
from qrvm.native_abi_contract import NativeABIContractError


class FakeFunction:
    def __init__(self, result=None):
        self.result = result
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return self.result


class FakeLibrary:
    def __init__(self, init=1):
        self.vq_sdl3_init_events = FakeFunction(init)
        self.vq_sdl3_quit_events = FakeFunction()
        self.vq_sdl3_last_error = FakeFunction(b'init failure')


class EventSessionTests(unittest.TestCase):
    def make_session(self, library):
        with patch('ctypes.CDLL', return_value=library):
            with patch('pathlib.Path.resolve', return_value=Path('/fake/libshim.so')):
                return SDL3EventSession(Path('/fake/libshim.so'))

    def test_poll_before_enter_rejected(self):
        session = self.make_session(FakeLibrary())
        with self.assertRaises(NativeABIContractError):
            session.poll()

    def test_successful_lifecycle(self):
        library = FakeLibrary()
        session = self.make_session(library)
        poller = type('Poller', (), {'poll': lambda self: None})()
        with patch('bindings.sdl3_native_poll.create_sdl3_poller', return_value=(poller, {'keydown': 12})):
            with session as opened:
                self.assertIs(opened, session)
                self.assertEqual(session.event_ids['keydown'], 12)
                self.assertIsNone(session.poll())
                with self.assertRaises(NativeABIContractError):
                    session.__enter__()
        self.assertEqual(library.vq_sdl3_quit_events.calls, 1)
        session.close()
        self.assertEqual(library.vq_sdl3_quit_events.calls, 1)

    def test_initialization_failure_propagates_error(self):
        library = FakeLibrary(init=0)
        session = self.make_session(library)
        with self.assertRaisesRegex(NativeABIContractError, 'init failure'):
            session.__enter__()
        self.assertEqual(library.vq_sdl3_quit_events.calls, 0)

    def test_probe_failure_releases_sdl(self):
        library = FakeLibrary()
        session = self.make_session(library)
        with patch('bindings.sdl3_native_poll.create_sdl3_poller', side_effect=ValueError('bad ABI')):
            with self.assertRaisesRegex(ValueError, 'bad ABI'):
                session.__enter__()
        self.assertEqual(library.vq_sdl3_quit_events.calls, 1)

    def test_real_sdl3_session(self):
        if not shutil.which('cc') or not shutil.which('pkg-config'):
            self.skipTest('C toolchain unavailable')
        if subprocess.run(['pkg-config', '--exists', 'sdl3'], check=False).returncode:
            self.skipTest('SDL3 development files unavailable')
        with tempfile.TemporaryDirectory() as directory:
            library = compile_sdl3_poll_shim(Path(directory) / 'libvq_sdl3_poll.so')
            with SDL3EventSession(library) as session:
                self.assertIn('keydown', session.event_ids)
                self.assertIsNone(session.poll())


if __name__ == '__main__':
    unittest.main()
