"""SDL2 event ABI smoke probe, without assuming an unverified SDL_Event layout."""
import ctypes
import ctypes.util
import unittest

from qrvm.native_composite_layout import NativeArrayType, NativeCompositeLayout


class SDLEventProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        name = ctypes.util.find_library('SDL2') or ctypes.util.find_library('SDL2-2.0') or 'libSDL2-2.0.so.0'
        if not name:
            raise unittest.SkipTest('SDL2 runtime unavailable')
        
        try:
            cls.sdl = ctypes.CDLL(name)
        except OSError:
            raise unittest.SkipTest('SDL2 runtime unavailable')
        cls.sdl.SDL_Init.argtypes = [ctypes.c_uint32]
        cls.sdl.SDL_Init.restype = ctypes.c_int
        cls.sdl.SDL_Quit.argtypes = []
        cls.sdl.SDL_Quit.restype = None
        cls.sdl.SDL_PushEvent.argtypes = [ctypes.c_void_p]
        cls.sdl.SDL_PushEvent.restype = ctypes.c_int
        cls.sdl.SDL_PollEvent.argtypes = [ctypes.c_void_p]
        cls.sdl.SDL_PollEvent.restype = ctypes.c_int
        if cls.sdl.SDL_Init(0x4000) != 0:  # SDL_INIT_EVENTS
            raise unittest.SkipTest('SDL event subsystem unavailable')

    @classmethod
    def tearDownClass(cls):
        cls.sdl.SDL_Quit()

    def test_opaque_event_storage_alignment(self):
        # Deliberately oversized, aligned storage; NOT a claim about sizeof(SDL_Event).
        layout = NativeCompositeLayout('SDLEventProbeStorage', 'union', (
            ('words', NativeArrayType('u64', 32)),
        ))
        self.assertGreaterEqual(layout.describe()['size'], 56)
        self.assertGreaterEqual(layout.describe()['alignment'], 8)

    def test_push_and_poll_quit_event(self):
        # Probe the runtime's event queue using aligned, oversized storage.
        layout = NativeCompositeLayout('SDLEventProbeStorage', 'union', (
            ('words', NativeArrayType('u64', 32)),
        ))
        storage_type = layout.ctypes_type()
        outgoing = storage_type()
        incoming = storage_type()
        ctypes.c_uint32.from_address(ctypes.addressof(outgoing)).value = 0x100  # SDL_QUIT
        self.assertEqual(self.sdl.SDL_PushEvent(ctypes.byref(outgoing)), 1)
        found = False
        for _ in range(128):
            if self.sdl.SDL_PollEvent(ctypes.byref(incoming)) != 1:
                break
            event_type = ctypes.c_uint32.from_address(ctypes.addressof(incoming)).value
            if event_type == 0x100:
                found = True
                break
        self.assertTrue(found, 'SDL_QUIT was not returned from the SDL2 event queue')


if __name__ == '__main__':
    unittest.main()
