"""End-to-end SDL2 event queue probe through Visual Quar source and QRVM.

The buffer is deliberately oversized; this is not SDL_Event ABI validation.
"""
import ctypes
import ctypes.util
import os
import subprocess
from pathlib import Path
import unittest

from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from frontend.quar.semantic import SemanticAnalyzer
from qrvm.compiler import QRVMCompiler
from qrvm.native_composite_layout import NativeArrayType, NativeCompositeLayout
from qrvm.native_ffi import NativeLibrary
from qrvm.vm import QRVM

SOURCE = '''extern "C" struct EventStorage { u64 words; };
extern "C" i32 SDL_PollEvent(out EventStorage event);
bytes event = SDL_PollEvent();
'''


class SDLSourceEventTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        name = ctypes.util.find_library('SDL2') or ctypes.util.find_library('SDL2-2.0') or 'libSDL2-2.0.so.0'
        try:
            cls.sdl = ctypes.CDLL(name)
        except (OSError, TypeError):
            raise unittest.SkipTest('SDL2 runtime unavailable')
        cls.sdl.SDL_Init.argtypes = [ctypes.c_uint32]
        cls.sdl.SDL_Init.restype = ctypes.c_int
        cls.sdl.SDL_Quit.argtypes = []
        cls.sdl.SDL_PushEvent.argtypes = [ctypes.c_void_p]
        cls.sdl.SDL_PushEvent.restype = ctypes.c_int
        cls.sdl.SDL_FlushEvents.argtypes = [ctypes.c_uint32, ctypes.c_uint32]
        cls.sdl.SDL_FlushEvents.restype = None
        cls.old_driver = os.environ.get('SDL_VIDEODRIVER')
        os.environ['SDL_VIDEODRIVER'] = 'dummy'
        if cls.sdl.SDL_Init(0x4000) != 0:
            raise unittest.SkipTest('SDL2 event subsystem unavailable')
        library_path = next((Path(line.split(' => ', 1)[1].strip()) for line in subprocess.run(['ldconfig', '-p'], capture_output=True, text=True, check=True).stdout.splitlines() if 'libSDL2-2.0.so.0 ' in line and ' => ' in line), None)
        if library_path is None:
            raise unittest.SkipTest('SDL2 library path unavailable')
        cls.library_path = library_path
        ast = Parser(Lexer(SOURCE).tokenize()).parse()
        SemanticAnalyzer().analyze(ast)
        cls.package = QRVMCompiler().compile(ast)
        cls.layout = NativeCompositeLayout('EventStorage', 'struct', (
            ('words', NativeArrayType('u64', 32)),
        ))

    @classmethod
    def tearDownClass(cls):
        cls.sdl.SDL_Quit()
        if cls.old_driver is None:
            os.environ.pop('SDL_VIDEODRIVER', None)
        else:
            os.environ['SDL_VIDEODRIVER'] = cls.old_driver

    def setUp(self):
        self.sdl.SDL_FlushEvents(0, 0xffffffff)

    def execute_source(self):
        vm = QRVM()
        vm.bind_native({}, NativeLibrary(self.library_path),
                       output_layouts={'SDL_PollEvent': self.layout},
                       output_success_statuses={'SDL_PollEvent': (1,)},
                       output_empty_statuses={'SDL_PollEvent': (0,)})
        variables = {}
        vm.execute(self.package['instructions'], variables)
        return variables['event']

    def test_empty_event_queue_returns_none(self):
        self.assertIsNone(self.execute_source())

    def test_pushed_quit_event_is_read_by_visual_quar(self):
        outgoing = self.layout.ctypes_type()()
        ctypes.c_uint32.from_address(ctypes.addressof(outgoing)).value = 0x100
        self.assertEqual(self.sdl.SDL_PushEvent(ctypes.byref(outgoing)), 1)
        event = self.execute_source()
        self.assertIs(type(event), bytes)
        self.assertEqual(int.from_bytes(event[:4], 'little'), 0x100)


if __name__ == '__main__':
    unittest.main()
