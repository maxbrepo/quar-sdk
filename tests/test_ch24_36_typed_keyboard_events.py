"""Typed external keyboard snapshots through a compiler-verified C fixture."""
import ctypes
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from bindings.sdl2_events import decode_sdl_event, decode_sdl_keyboard_event
from qrvm.native_abi_contract import NativeABIContractError, NativeOutputABIContract
from qrvm.native_ffi import NativeLibrary
from qrvm.vm import QRVM
from qrvm.instructions import OpCode


class TypedKeyboardEventsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = shutil.which('cc')
        if compiler is None:
            raise unittest.SkipTest('C compiler unavailable')
        cls.temp = tempfile.TemporaryDirectory()
        cls.library_path = Path(cls.temp.name) / 'libkeyboard_fixture.so'
        source = Path(__file__).resolve().parents[1] / 'fixtures/qgf_ffi_keyboard_event.c'
        subprocess.run([compiler, '-std=c11', '-shared', '-fPIC', str(source), '-o', str(cls.library_path)],
                       capture_output=True, text=True, check=True)
        cls.lib = ctypes.CDLL(str(cls.library_path))
        names = ('size', 'alignment', 'type_offset', 'scancode_offset', 'sym_offset')
        for name in names:
            getattr(cls.lib, 'qgf_keyboard_' + name).restype = ctypes.c_size_t
        cls.contract = NativeOutputABIContract(
            cls.lib.qgf_keyboard_size(), cls.lib.qgf_keyboard_alignment(),
            (('type', cls.lib.qgf_keyboard_type_offset()),
             ('key_scancode', cls.lib.qgf_keyboard_scancode_offset()),
             ('key_sym', cls.lib.qgf_keyboard_sym_offset())),
        )

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def _event_bytes(self):
        vm = QRVM()
        vm.bind_native({}, NativeLibrary(self.library_path),
                       output_layouts={'qgf_poll_keyboard': self.contract.opaque_storage('FixtureKeyboardEvent')},
                       output_success_statuses={'qgf_poll_keyboard': (1,)},
                       output_empty_statuses={'qgf_poll_keyboard': (0,)})
        vm.execute([(OpCode.CALL, ('qgf_poll_keyboard', 0))], {})
        return vm.stack[-1]

    def test_verified_keyboard_event_through_qrvm(self):
        event = decode_sdl_keyboard_event(self._event_bytes(), self.contract)
        self.assertEqual((event.type, event.scancode, event.keycode), (0x300, 4, -42))
        self.assertEqual(len(event.raw), self.contract.size)

    def test_empty_is_none(self):
        self.assertIsNone(decode_sdl_keyboard_event(None, self.contract))

    def test_non_keyboard_event_does_not_decode_keyboard_fields(self):
        raw = bytearray(self._event_bytes())
        raw[0:4] = (0x100).to_bytes(4, __import__('sys').byteorder)
        minimal = NativeOutputABIContract(self.contract.size, self.contract.alignment, (('type', 0),))
        self.assertIsNone(decode_sdl_keyboard_event(bytes(raw), minimal))
        self.assertEqual(decode_sdl_event(bytes(raw), minimal).type, 0x100)

    def test_missing_keyboard_field_rejected(self):
        raw = self._event_bytes()
        missing = NativeOutputABIContract(self.contract.size, self.contract.alignment,
                                          (('type', 0), ('key_scancode', 4)))
        with self.assertRaises(NativeABIContractError):
            decode_sdl_keyboard_event(raw, missing)

    def test_invalid_buffer_length_rejected(self):
        with self.assertRaises(NativeABIContractError):
            decode_sdl_keyboard_event(b'\x00' * (self.contract.size - 1), self.contract)

    def test_unaligned_offset_rejected(self):
        invalid = NativeOutputABIContract(self.contract.size, self.contract.alignment,
                                          (('type', 0), ('key_scancode', 5), ('key_sym', 8)))
        with self.assertRaises(NativeABIContractError):
            decode_sdl_keyboard_event(self._event_bytes(), invalid)


if __name__ == '__main__':
    unittest.main()
