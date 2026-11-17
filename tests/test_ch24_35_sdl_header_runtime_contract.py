"""SDL_Event ABI validation against the *installed* SDL2 C headers.

This integration gate skips when SDL2 development headers are unavailable.
No SDL_Event size, alignment or field offset is assumed in the binding.
"""
import ctypes
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest

from bindings.sdl2_events import decode_sdl_event, decode_sdl_keyboard_event
from qrvm.native_abi_contract import NativeOutputABIContract
from qrvm.native_ffi import NativeLibrary
from qrvm.vm import QRVM
from qrvm.instructions import OpCode


class SDLHeaderRuntimeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = shutil.which('cc')
        if not compiler:
            raise unittest.SkipTest('C compiler unavailable')
        config = shutil.which('sdl2-config')
        pkg = shutil.which('pkg-config')
        if config:
            flags = subprocess.run([config, '--cflags', '--libs'], capture_output=True, text=True)
        elif pkg:
            flags = subprocess.run([pkg, '--cflags', '--libs', 'sdl2'], capture_output=True, text=True)
        else:
            raise unittest.SkipTest('SDL2 development tools unavailable')
        if flags.returncode:
            raise unittest.SkipTest('SDL2 development headers unavailable')
        cls.temp = tempfile.TemporaryDirectory()
        root = Path(cls.temp.name)
        source = root / 'probe.c'
        source.write_text('''#include <SDL.h>
#include <stddef.h>
#include <stdint.h>
#include <stdalign.h>
size_t vq_event_size(void) { return sizeof(SDL_Event); }
size_t vq_event_align(void) { return alignof(SDL_Event); }
size_t vq_event_type_offset(void) { return offsetof(SDL_Event, type); }
size_t vq_event_key_scancode_offset(void) { return offsetof(SDL_Event, key.keysym.scancode); }
size_t vq_event_key_sym_offset(void) { return offsetof(SDL_Event, key.keysym.sym); }
int32_t vq_key_a(void) { return SDLK_a; }
int32_t vq_scan_a(void) { return SDL_SCANCODE_A; }
int32_t vq_poll_event(SDL_Event *event) { return SDL_PollEvent(event); }
int32_t vq_push_keydown(void) {
    SDL_Event event = {0};
    event.type = SDL_KEYDOWN;
    event.key.keysym.scancode = SDL_SCANCODE_A;
    event.key.keysym.sym = SDLK_a;
    return SDL_PushEvent(&event);
}
int32_t vq_push_quit(void) {
    SDL_Event event = {0};
    event.type = SDL_QUIT;
    return SDL_PushEvent(&event);
}
''', encoding='utf-8')
        cls.library_path = root / 'libvq_sdl_event_probe.so'
        # Link flags after source for linkers that resolve libraries left to right.
        command = [compiler, '-std=c11', '-shared', '-fPIC', str(source), '-o', str(cls.library_path), *shlex.split(flags.stdout)]
        build = subprocess.run(command, capture_output=True, text=True)
        if build.returncode:
            cls.temp.cleanup()
            raise AssertionError('SDL2 header probe compilation failed: ' + build.stderr)
        cls.lib = ctypes.CDLL(str(cls.library_path))
        for name in ('vq_event_size', 'vq_event_align', 'vq_event_type_offset', 'vq_event_key_scancode_offset', 'vq_event_key_sym_offset'):
            getattr(cls.lib, name).restype = ctypes.c_size_t
        cls.lib.SDL_Init.argtypes = [ctypes.c_uint32]
        cls.lib.SDL_Init.restype = ctypes.c_int
        cls.lib.SDL_Quit.argtypes = []
        cls.lib.SDL_Quit.restype = None
        cls.lib.SDL_FlushEvents.argtypes = [ctypes.c_uint32, ctypes.c_uint32]
        cls.lib.SDL_FlushEvents.restype = None
        for name in ('vq_key_a', 'vq_scan_a', 'vq_push_keydown'):
            getattr(cls.lib, name).argtypes = []
            getattr(cls.lib, name).restype = ctypes.c_int32
        cls.lib.vq_push_quit.argtypes = []
        cls.lib.vq_push_quit.restype = ctypes.c_int32
        cls.old_driver = os.environ.get('SDL_VIDEODRIVER')
        os.environ['SDL_VIDEODRIVER'] = 'dummy'
        if cls.lib.SDL_Init(0x4000) != 0:
            cls._cleanup()
            raise unittest.SkipTest('SDL event subsystem unavailable')
        cls.initialized = True
        cls.contract = NativeOutputABIContract(
            int(cls.lib.vq_event_size()), int(cls.lib.vq_event_align()),
            (('type', int(cls.lib.vq_event_type_offset())),
             ('key_scancode', int(cls.lib.vq_event_key_scancode_offset())),
             ('key_sym', int(cls.lib.vq_event_key_sym_offset()))),
        )

    @classmethod
    def _cleanup(cls):
        if getattr(cls, 'initialized', False):
            cls.lib.SDL_Quit()
        if cls.old_driver is None:
            os.environ.pop('SDL_VIDEODRIVER', None)
        else:
            os.environ['SDL_VIDEODRIVER'] = cls.old_driver
        cls.temp.cleanup()

    @classmethod
    def tearDownClass(cls):
        cls._cleanup()

    def setUp(self):
        self.lib.SDL_FlushEvents(0, 0xffffffff)

    def _poll_raw(self):
        vm = QRVM()
        vm.bind_native({}, NativeLibrary(self.library_path),
                       output_layouts={'vq_poll_event': self.contract.opaque_storage('HeaderVerifiedEvent')},
                       output_success_statuses={'vq_poll_event': (1,)},
                       output_empty_statuses={'vq_poll_event': (0,)})
        vm.execute([(OpCode.CALL, ('vq_poll_event', 0))], {})
        return vm.stack[-1]

    def _poll(self):
        return decode_sdl_event(self._poll_raw(), self.contract)

    def test_exact_storage_matches_compiled_sdl_event(self):
        layout = self.contract.opaque_storage('HeaderVerifiedEvent')
        self.assertEqual(layout.describe()['size'], self.lib.vq_event_size())
        self.assertEqual(layout.describe()['alignment'], self.lib.vq_event_align())
        offsets = dict(self.contract.offsets)
        self.assertEqual(offsets['type'], 0)
        for field in ('key_scancode', 'key_sym'):
            self.assertGreaterEqual(offsets[field], 0)
            self.assertEqual(offsets[field] % 4, 0)
            self.assertLessEqual(offsets[field] + 4, self.contract.size)

    def test_real_sdl_queue_empty_and_quit_through_qrvm(self):
        self.assertIsNone(self._poll())
        self.assertEqual(self.lib.vq_push_quit(), 1)
        event = self._poll()
        self.assertIsNotNone(event)
        self.assertEqual(event.type, 0x100)
        self.assertEqual(len(event.raw), self.contract.size)

    def test_real_sdl_event_from_visual_quar_source(self):
        """The source-declared output storage must match the measured SDL ABI."""
        from frontend.quar.lexer import Lexer
        from frontend.quar.parser import Parser
        from frontend.quar.semantic import SemanticAnalyzer
        from qrvm.compiler import QRVMCompiler
        from qrvm.native_composite_layout import NativeCompositeLayout

        scalar = 'u64' if self.contract.alignment == 8 else 'u32'
        field_count = self.contract.size // self.contract.alignment
        fields = ' '.join(f'{scalar} word_{index};' for index in range(field_count))
        source = ('extern "C" struct SDLEventStorage { ' + fields + ' }; '
                  'extern "C" i32 vq_poll_event(out SDLEventStorage event); '
                  'bytes result = vq_poll_event();')
        ast = Parser(Lexer(source).tokenize()).parse()
        SemanticAnalyzer().analyze(ast)
        package = QRVMCompiler().compile(ast)
        layout = NativeCompositeLayout('SDLEventStorage', 'struct',
                                       tuple(package['native_struct_layouts']['SDLEventStorage']))
        self.assertEqual(layout.describe()['size'], self.contract.size)
        self.assertEqual(layout.describe()['alignment'], self.contract.alignment)
        vm = QRVM()
        vm.bind_native({}, NativeLibrary(self.library_path),
                       output_layouts={'vq_poll_event': layout},
                       declared_output_layouts={'vq_poll_event': layout},
                       output_success_statuses={'vq_poll_event': (1,)},
                       output_empty_statuses={'vq_poll_event': (0,)})
        variables = {}
        vm.execute(package['instructions'], variables)
        self.assertIsNone(variables['result'])
        self.assertEqual(self.lib.vq_push_keydown(), 1)
        variables = {}
        vm.execute(package['instructions'], variables)
        event = decode_sdl_keyboard_event(variables['result'], self.contract)
        self.assertEqual(event.scancode, self.lib.vq_scan_a())
        self.assertEqual(event.keycode, self.lib.vq_key_a())

    def test_real_sdl_keyboard_event_through_qrvm(self):
        self.assertEqual(self.lib.vq_push_keydown(), 1)
        event = decode_sdl_keyboard_event(self._poll_raw(), self.contract)
        self.assertIsNotNone(event)
        self.assertEqual(event.type, 0x300)
        self.assertEqual(event.scancode, self.lib.vq_scan_a())
        self.assertEqual(event.keycode, self.lib.vq_key_a())


if __name__ == '__main__':
    unittest.main()
