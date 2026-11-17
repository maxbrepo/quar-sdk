"""Exercise the SDL3 Visual Quar window examples against a deterministic C ABI stub.

This does not replace real SDL3 integration tests: it validates the QRVM/FFI
call sequence independently of installed SDL3 and display-server availability.
"""
from __future__ import annotations

import ctypes
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from frontend.quar.semantic import SemanticAnalyzer
from main import run_qrvm

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / 'examples' / '0.0.5' / 'typed' / '24_interoperability'

STUB = r'''
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
static unsigned init_count, quit_count, create_count, destroy_count, delay_count;
static void trace(const char *event) {
    const char *path = getenv("VQ_CH24_TRACE");
    if (!path) return;
    FILE *file = fopen(path, "a");
    if (!file) return;
    fprintf(file, "%s\n", event);
    fclose(file);
}
bool SDL_Init(uint32_t flags) { init_count++; trace("init"); return flags == 32; }
void *SDL_CreateWindow(const char *title, int32_t width, int32_t height, uint64_t flags) {
    (void)title; (void)flags;
    create_count++; trace("create");
    if (width <= 0 || height <= 0) return NULL;
    return malloc(1);
}
void SDL_DestroyWindow(void *window) {
    destroy_count++; trace("destroy"); free(window);
}
void SDL_Quit(void) { quit_count++; trace("quit"); }
void SDL_Delay(uint32_t milliseconds) { (void)milliseconds; delay_count++; trace("delay"); }
'''

CASES = {
    '24_73_sdl3_window_basic': ['init', 'create', 'destroy', 'quit'],
    '24_74_sdl3_window_delay': ['init', 'create', 'delay', 'destroy', 'quit'],
    '24_75_sdl3_two_windows': ['init', 'create', 'create', 'destroy', 'destroy', 'quit'],
    '24_76_sdl3_reinitialize': ['init', 'create', 'destroy', 'quit', 'init', 'create', 'destroy', 'quit'],
}


class SDL3StubLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('gcc'):
            raise unittest.SkipTest('gcc required for the native ABI stub')
        cls.temp = tempfile.TemporaryDirectory(prefix='vq_ch24_sdl3_stub_')
        cls.addClassCleanup(cls.temp.cleanup)
        directory = Path(cls.temp.name)
        source = directory / 'sdl3_stub.c'
        cls.library = directory / 'libvq_sdl3_stub.so'
        source.write_text(STUB, encoding='utf-8')
        subprocess.run(['gcc', '-std=c11', '-shared', '-fPIC', '-Wall', '-Wextra',
                        '-o', str(cls.library), str(source)], check=True, capture_output=True)

    def test_window_examples_native_call_sequence(self):
        for name, expected in CASES.items():
            with self.subTest(name=name):
                trace = Path(self.temp.name) / (name + '.trace')
                source = (EXAMPLES / (name + '.vq')).read_text(encoding='utf-8')
                program = Parser(Lexer(source).tokenize()).parse()
                SemanticAnalyzer().analyze(program)
                with patch.dict(os.environ, {'VQ_CH24_TRACE': str(trace)}):
                    run_qrvm(program, native_library=str(self.library),
                             native_release_symbols=('SDL_DestroyWindow',))
                self.assertEqual(trace.read_text(encoding='utf-8').splitlines(), expected)

    def test_stub_abi_bool_and_null_pointer(self):
        stub = ctypes.CDLL(str(self.library))
        stub.SDL_Init.argtypes = [ctypes.c_uint32]
        stub.SDL_Init.restype = ctypes.c_bool
        self.assertTrue(stub.SDL_Init(32))
        self.assertFalse(stub.SDL_Init(0))
        stub.SDL_CreateWindow.argtypes = [ctypes.c_char_p, ctypes.c_int32,
                                          ctypes.c_int32, ctypes.c_uint64]
        stub.SDL_CreateWindow.restype = ctypes.c_void_p
        self.assertIsNone(stub.SDL_CreateWindow(b'bad', 0, 240, 0))


if __name__ == '__main__':
    unittest.main()
