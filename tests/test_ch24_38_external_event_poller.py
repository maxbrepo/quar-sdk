"""Exercise the optional event poller with C fixtures, not hardcoded SDL ABI."""
import ctypes
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from bindings.sdl2_events import SDLEventPoller
from qrvm.native_abi_contract import NativeABIContractError, NativeOutputABIContract


class ExternalEventPollerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = shutil.which('cc')
        if compiler is None:
            raise unittest.SkipTest('C compiler unavailable')
        cls.temp = tempfile.TemporaryDirectory()
        cls.library = Path(cls.temp.name) / 'libpoller.so'
        fixture = Path(__file__).resolve().parents[1] / 'fixtures/qgf_ffi_keyboard_event.c'
        subprocess.run([compiler, '-std=c11', '-shared', '-fPIC', str(fixture), '-o', str(cls.library)],
                       check=True, capture_output=True, text=True)
        probe = ctypes.CDLL(str(cls.library))
        for name in ('size', 'alignment', 'type_offset', 'scancode_offset', 'sym_offset'):
            getattr(probe, 'qgf_keyboard_' + name).restype = ctypes.c_size_t
        cls.contract = NativeOutputABIContract(
            probe.qgf_keyboard_size(), probe.qgf_keyboard_alignment(),
            (('type', probe.qgf_keyboard_type_offset()),
             ('key_scancode', probe.qgf_keyboard_scancode_offset()),
             ('key_sym', probe.qgf_keyboard_sym_offset())),
        )

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_poll_copied_event_and_stack_cleanup(self):
        poller = SDLEventPoller(str(self.library), 'qgf_poll_keyboard', self.contract)
        for _ in range(3):
            event = poller.poll()
            self.assertEqual(event.type, 0x300)
            self.assertEqual(len(event.raw), self.contract.size)
            self.assertEqual(poller.vm.stack, [])

    def test_poll_keyboard_decodes_verified_fields(self):
        poller = SDLEventPoller(str(self.library), 'qgf_poll_keyboard', self.contract)
        event = poller.poll_keyboard()
        self.assertEqual((event.type, event.scancode, event.keycode), (0x300, 4, -42))
        self.assertEqual(poller.vm.stack, [])

    def test_invalid_contract_is_rejected(self):
        with self.assertRaises(NativeABIContractError):
            SDLEventPoller(str(self.library), 'qgf_poll_keyboard', None)

    def test_invalid_symbol_is_rejected(self):
        with self.assertRaises(NativeABIContractError):
            SDLEventPoller(str(self.library), 'invalid-symbol', self.contract)


if __name__ == '__main__':
    unittest.main()
