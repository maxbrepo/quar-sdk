"""SDL3 header ABI validation; runs real compiler integration when available."""
import json
import shutil
import struct
import subprocess
import unittest

from bindings.sdl3_abi_probe import measure_sdl3_abi, parse_sdl3_probe
from bindings.sdl3_events import decode_sdl3_keyboard_event, decode_sdl3_mouse_motion_event
from qrvm.native_abi_contract import NativeABIContractError


class SDL3ABIProbeTests(unittest.TestCase):
    def setUp(self):
        self.sample = {'size': 64, 'alignment': 8,
                       'offsets': {'type': 0, 'key_scancode': 16, 'key_key': 20,
                                   'motion_x': 24, 'motion_y': 28},
                       'event_ids': {'keydown': 0x300, 'keyup': 0x301, 'motion': 0x400}}

    def test_valid_contract(self):
        contract, ids = parse_sdl3_probe(json.dumps(self.sample))
        self.assertEqual((contract.size, ids['keydown']), (64, 0x300))

    def test_missing_field(self):
        del self.sample['offsets']['motion_y']
        with self.assertRaises(NativeABIContractError):
            parse_sdl3_probe(json.dumps(self.sample))

    def test_duplicate_event_id(self):
        self.sample['event_ids']['keyup'] = self.sample['event_ids']['keydown']
        with self.assertRaises(NativeABIContractError):
            parse_sdl3_probe(json.dumps(self.sample))

    def test_unaligned_offset(self):
        self.sample['offsets']['key_key'] = 21
        with self.assertRaises(NativeABIContractError):
            parse_sdl3_probe(json.dumps(self.sample))

    def test_out_of_bounds_offset(self):
        self.sample['offsets']['motion_y'] = 64
        with self.assertRaises(NativeABIContractError):
            parse_sdl3_probe(json.dumps(self.sample))

    def test_boolean_identifier_rejected(self):
        self.sample['event_ids']['motion'] = True
        with self.assertRaises(NativeABIContractError):
            parse_sdl3_probe(json.dumps(self.sample))

    def test_real_sdl3_headers(self):
        if not shutil.which('cc') or not shutil.which('pkg-config'):
            self.skipTest('C compiler or pkg-config unavailable')
        if subprocess.run(['pkg-config', '--exists', 'sdl3'], check=False).returncode:
            self.skipTest('SDL3 development headers unavailable')
        contract, ids = measure_sdl3_abi()
        self.assertGreaterEqual(contract.size, 32)
        self.assertNotEqual(ids['keydown'], ids['keyup'])
        raw = bytearray(contract.size)
        offsets = dict(contract.offsets)
        struct.pack_into('=I', raw, offsets['type'], ids['keydown'])
        struct.pack_into('=I', raw, offsets['key_scancode'], 4)
        struct.pack_into('=I', raw, offsets['key_key'], 97)
        event = decode_sdl3_keyboard_event(bytes(raw), contract, ids['keydown'], ids['keyup'])
        self.assertEqual((event.scancode, event.keycode), (4, 97))
        struct.pack_into('=I', raw, offsets['type'], ids['motion'])
        struct.pack_into('=f', raw, offsets['motion_x'], 5.5)
        struct.pack_into('=f', raw, offsets['motion_y'], -2.0)
        motion = decode_sdl3_mouse_motion_event(bytes(raw), contract, ids['motion'])
        self.assertEqual((motion.x, motion.y), (5.5, -2.0))


if __name__ == '__main__':
    unittest.main()
