"""Compare SDL_Event ABI against installed SDL2 headers when available."""
import ctypes
import shutil
import subprocess
import tempfile
from pathlib import Path
import unittest

from qrvm.native_composite_layout import NativeArrayType, NativeCompositeLayout


class SDLEventABIHeaderTests(unittest.TestCase):
    def test_sdl_event_size_alignment_and_type_offset(self):
        compiler = shutil.which('cc')
        config = shutil.which('sdl2-config')
        if not compiler or not config:
            self.skipTest('SDL2 development headers/compiler unavailable; ABI unverified')
        flags = subprocess.run([config, '--cflags'], capture_output=True, text=True)
        if flags.returncode:
            self.skipTest('SDL2 development flags unavailable')
        import shlex
        source = '''#include <SDL.h>
#include <stddef.h>
#include <stdio.h>
int main(void) {
    printf("%zu %zu %zu\\n", sizeof(SDL_Event), _Alignof(SDL_Event), offsetof(SDL_Event, type));
    return 0;
}
'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / 'probe.c').write_text(source, encoding='utf-8')
            build = subprocess.run([compiler, '-std=c11', *shlex.split(flags.stdout), str(path / 'probe.c'), '-o', str(path / 'probe')], capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            run = subprocess.run([str(path / 'probe')], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
        size, alignment, offset = map(int, run.stdout.strip().split())
        self.assertEqual(offset, 0, 'SDL_Event.type must be at offset zero for the probe')
        # Storage capacity is not equivalent to an exact SDL_Event ABI layout.
        storage = NativeCompositeLayout('SDLEventProbeStorage31', 'union', (
            ('words', NativeArrayType('u64', 32)),
        ))
        self.assertGreaterEqual(storage.describe()['size'], size)
        self.assertGreaterEqual(storage.describe()['alignment'], alignment)
        self.assertEqual(ctypes.sizeof(ctypes.c_uint32), 4)

    def test_source_event_declaration_does_not_match_runtime_buffer(self):
        # Explicitly expose the current mismatch; do not certify a typed binding.
        source_size = ctypes.sizeof(ctypes.c_uint64)
        buffer_size = NativeCompositeLayout('EventStorage31', 'struct', (
            ('words', NativeArrayType('u64', 32)),
        )).describe()['size']
        self.assertNotEqual(source_size, buffer_size)


if __name__ == '__main__':
    unittest.main()
