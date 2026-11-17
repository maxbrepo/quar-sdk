"""Check the SDL2 graphical-window example without requiring a display."""
import ctypes.util
import contextlib
import io
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from frontend.quar.semantic import SemanticAnalyzer
from main import run_qrvm


EXAMPLE = (Path(__file__).resolve().parents[1] / "examples" / "0.0.5" /
           "typed" / "24_interoperability" / "24_14_sdl_visible_window.vq")


class SDLWindowExampleTests(unittest.TestCase):
    def test_example_parses_and_analyzes(self):
        program = Parser(Lexer(EXAMPLE.read_text(encoding="utf-8")).tokenize()).parse()
        SemanticAnalyzer().analyze(program)

    def test_example_runs_with_dummy_backend(self):
        library = ctypes.util.find_library("SDL2")
        folders = ("/usr/lib/x86_64-linux-gnu", "/lib/x86_64-linux-gnu",
                   "/usr/lib/aarch64-linux-gnu", "/lib/aarch64-linux-gnu")
        path = next((str(Path(folder) / name) for folder in folders
                     for name in (library, "libSDL2-2.0.so.0")
                     if name and (Path(folder) / name).is_file()), None)
        if path is None:
            self.skipTest("SDL2 shared library not installed")
        program = Parser(Lexer(EXAMPLE.read_text(encoding="utf-8")).tokenize()).parse()
        SemanticAnalyzer().analyze(program)
        with patch.dict(os.environ, {"SDL_VIDEODRIVER": "dummy"}):
            with contextlib.redirect_stdout(io.StringIO()):
                run_qrvm(program, native_library=path,
                         native_release_symbols=("SDL_DestroyWindow",))


if __name__ == "__main__":
    unittest.main()
