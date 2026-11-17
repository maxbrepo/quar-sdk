"""SDL3 polling adapter tests; real SDL3 test runs only when installed."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from bindings.sdl3_native_poll import compile_sdl3_poll_shim, create_sdl3_poller
from qrvm.native_abi_contract import NativeABIContractError


class SDL3NativePollTests(unittest.TestCase):
    def test_missing_source_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(NativeABIContractError):
                compile_sdl3_poll_shim(Path(directory) / 'out.so', Path(directory) / 'missing.c')

    def test_compiler_invocation_uses_pkg_config_flags(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'adapter.c'
            source.write_text('int unused(void) {return 0;}')
            with patch('bindings.sdl3_native_poll.subprocess.run') as run:
                run.return_value.stdout = '-I/usr/include/mock -lSDL3'
                output = compile_sdl3_poll_shim(Path(directory) / 'adapter.so', source)
                self.assertEqual(output.name, 'adapter.so')
                self.assertEqual(run.call_count, 2)
                command = run.call_args.args[0]
                self.assertIn('-shared', command)
                self.assertIn('-lSDL3', command)

    def test_real_sdl3_poll_empty_queue(self):
        if not shutil.which('cc') or not shutil.which('pkg-config'):
            self.skipTest('C compiler or pkg-config unavailable')
        if subprocess.run(['pkg-config', '--exists', 'sdl3'], check=False).returncode:
            self.skipTest('SDL3 development files unavailable')
        with tempfile.TemporaryDirectory() as directory:
            library = compile_sdl3_poll_shim(Path(directory) / 'libvq_sdl3_poll.so')
            poller, ids = create_sdl3_poller(library)
            self.assertIn('keydown', ids)
            # SDL is not initialized: no event is expected; output remains opaque.
            self.assertIsNone(poller.poll())


if __name__ == '__main__':
    unittest.main()
