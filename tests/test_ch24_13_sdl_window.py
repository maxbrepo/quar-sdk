"""Open and close a real SDL2 window using the dummy video backend."""
import ctypes.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from frontend.quar.semantic import SemanticAnalyzer
from main import run_qrvm


class SDLWindowTests(unittest.TestCase):
    def test_window_create_destroy(self):
        names = (ctypes.util.find_library('SDL2'), 'libSDL2-2.0.so.0')
        folders = ('/usr/lib/x86_64-linux-gnu', '/lib/x86_64-linux-gnu',
                   '/usr/lib/aarch64-linux-gnu', '/lib/aarch64-linux-gnu')
        path = next((str(Path(folder) / name) for folder in folders for name in names
                     if name and (Path(folder) / name).is_file()), None)
        if path is None:
            self.skipTest('SDL2 library not found')
        source = ('extern "C" i32 SDL_Init(u32 flags); '
                  'extern "C" opaque SDL_CreateWindow(cstring title, i32 x, i32 y, i32 w, i32 h, u32 flags); '
                  'extern "C" void SDL_DestroyWindow(opaque window); '
                  'extern "C" void SDL_Quit(); '
                  'u32 flags = 0; i32 status = SDL_Init(flags); '
                  'window = SDL_CreateWindow("Visual Quar – prova", 0, 0, 320, 240, flags); '
                  'SDL_DestroyWindow(window); SDL_Quit();')
        program = Parser(Lexer(source).tokenize()).parse()
        SemanticAnalyzer().analyze(program)
        with patch.dict(os.environ, {'SDL_VIDEODRIVER': 'dummy'}):
            run_qrvm(program, native_library=path, native_release_symbols=('SDL_DestroyWindow',))
