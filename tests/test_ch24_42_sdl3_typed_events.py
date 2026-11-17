"""SDL3 typed event decoding against a simulated header-measured ABI."""
import struct
import unittest
from bindings.sdl3_events import decode_sdl3_keyboard_event, decode_sdl3_mouse_motion_event
from qrvm.native_abi_contract import NativeABIContractError, NativeOutputABIContract

class SDL3TypedEventsTests(unittest.TestCase):
    def setUp(self):
        self.contract = NativeOutputABIContract(32, 8, (
            ('type', 0), ('key_scancode', 8), ('key_key', 12),
            ('motion_x', 16), ('motion_y', 20)))

    def raw(self, event_type):
        data = bytearray(32)
        struct.pack_into('=I', data, 0, event_type)
        struct.pack_into('=I', data, 8, 42)
        struct.pack_into('=I', data, 12, 0x4000004f)
        struct.pack_into('=f', data, 16, 12.5)
        struct.pack_into('=f', data, 20, -3.25)
        return bytes(data)

    def test_keydown(self):
        event = decode_sdl3_keyboard_event(self.raw(0x300), self.contract, 0x300, 0x301)
        self.assertEqual((event.scancode, event.keycode), (42, 0x4000004f))

    def test_keyup(self):
        self.assertEqual(decode_sdl3_keyboard_event(self.raw(0x301), self.contract, 0x300, 0x301).type, 0x301)

    def test_unrelated_event(self):
        self.assertIsNone(decode_sdl3_keyboard_event(self.raw(5), self.contract, 0x300, 0x301))

    def test_motion(self):
        event = decode_sdl3_mouse_motion_event(self.raw(0x400), self.contract, 0x400)
        self.assertEqual((event.x, event.y), (12.5, -3.25))

    def test_missing_field(self):
        contract = NativeOutputABIContract(32, 8, (('type', 0),))
        with self.assertRaises(NativeABIContractError):
            decode_sdl3_keyboard_event(self.raw(0x300), contract, 0x300, 0x301)

    def test_missing_motion_offset(self):
        contract = NativeOutputABIContract(32, 8, (('type', 0), ('motion_x', 16)))
        with self.assertRaises(NativeABIContractError):
            decode_sdl3_mouse_motion_event(self.raw(0x400), contract, 0x400)

if __name__ == '__main__':
    unittest.main()
