"""Exercise the generic Visual Quar C FFI against the real SDL2 runtime."""
import ctypes.util
import io
import contextlib
import unittest
from pathlib import Path

from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from frontend.quar.semantic import SemanticAnalyzer
from main import run_qrvm
from qrvm.native_ffi import NativeFFIError, NativeLibrary, NativeSignature


SDL_SOURCE = (
    'extern "C" i32 SDL_Init(u32 flags); '
    'extern "C" opaque SDL_CreateRGBSurface(u32 flags, i32 width, i32 height, '
    'i32 depth, u32 red, u32 green, u32 blue, u32 alpha); '
    'extern "C" void SDL_FreeSurface(opaque surface); '
    'extern "C" void SDL_Quit(); '
)


class SDL2SmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        library_name = ctypes.util.find_library("SDL2")
        # NativeLibrary intentionally requires an explicit existing file path.
        names = (library_name, "libSDL2-2.0.so.0", "libSDL2.so")
        candidates = tuple(
            Path(folder) / name
            for folder in ("/usr/lib/x86_64-linux-gnu", "/lib/x86_64-linux-gnu",
                           "/usr/lib/aarch64-linux-gnu", "/lib/aarch64-linux-gnu")
            for name in names if name
        )
        cls.path = next((path for path in candidates if path.is_file()), None)
        if cls.path is None:
            raise unittest.SkipTest("SDL2 located, but no explicit library path resolved")

    def run_source(self, body):
        program = Parser(Lexer(SDL_SOURCE + body).tokenize()).parse()
        SemanticAnalyzer().analyze(program)
        with contextlib.redirect_stdout(io.StringIO()):
            run_qrvm(program, native_library=str(self.path), native_release_symbols=("SDL_FreeSurface",))

    def test_sdl_initialization_and_shutdown(self):
        self.run_source('u32 flags = 0; i32 status = SDL_Init(flags); SDL_Quit();')

    def test_sdl_surface_lifecycle(self):
        self.run_source(
            'u32 flags = 0; i32 status = SDL_Init(flags); '
            'surface = SDL_CreateRGBSurface(flags, 16, 16, 32, flags, flags, flags, flags); '
            'SDL_FreeSurface(surface); SDL_Quit();'
        )

    def test_sdl_rejects_double_free(self):
        with self.assertRaisesRegex(NativeFFIError, "released"):
            self.run_source(
                'u32 flags = 0; i32 status = SDL_Init(flags); '
                'surface = SDL_CreateRGBSurface(flags, 16, 16, 32, flags, flags, flags, flags); '
                'SDL_FreeSurface(surface); SDL_FreeSurface(surface);'
            )
        # SDL_Quit must run even if the Visual Quar program raises.
        NativeLibrary(self.path).call(NativeSignature("SDL_Quit", (), "void"))


if __name__ == "__main__":
    unittest.main()
