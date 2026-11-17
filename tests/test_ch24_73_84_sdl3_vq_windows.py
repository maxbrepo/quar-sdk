"""SDL3 Visual Quar source checks and conditional native smoke tests."""
import ctypes.util
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from frontend.quar.semantic import SemanticAnalyzer
from main import run_qrvm

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / 'examples' / '0.0.5' / 'typed' / '24_interoperability'
NAMES = ('24_73_sdl3_window_basic', '24_74_sdl3_window_delay',
         '24_75_sdl3_two_windows', '24_76_sdl3_reinitialize')


class SDL3WindowExamples(unittest.TestCase):
    def test_source_parses_and_analyzes(self):
        for name in NAMES:
            with self.subTest(name=name):
                source = (EXAMPLES / (name + '.vq')).read_text()
                program = Parser(Lexer(source).tokenize()).parse()
                SemanticAnalyzer().analyze(program)

    def test_native_dependency_metadata(self):
        for name in NAMES:
            with self.subTest(name=name):
                meta = json.loads((EXAMPLES / (name + '.vq.native.json')).read_text())
                self.assertEqual(meta, {'regression_requires_native_library': 'SDL3'})

    def test_native_sdl3_window_lifecycle(self):
        lib = ctypes.util.find_library('SDL3')
        if not lib:
            self.skipTest('SDL3 shared library not available')
        for name in NAMES:
            with self.subTest(name=name):
                source = (EXAMPLES / (name + '.vq')).read_text()
                program = Parser(Lexer(source).tokenize()).parse()
                SemanticAnalyzer().analyze(program)
                with patch.dict(os.environ, {'SDL_VIDEODRIVER': 'dummy'}):
                    run_qrvm(program, native_library=lib,
                             native_release_symbols=('SDL_DestroyWindow',))
