"""Validate the optional SDL adapter against a real C-compiled event fixture."""
import ctypes
import shutil
import subprocess
import tempfile
from pathlib import Path
import unittest

from bindings.sdl2_events import SDLEventSnapshot, decode_sdl_event
from qrvm.native_abi_contract import NativeABIContractError, NativeOutputABIContract
from qrvm.native_ffi import NativeLibrary
from qrvm.vm import QRVM
from qrvm.instructions import OpCode


class ExternalEventBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = shutil.which('cc')
        if compiler is None:
            raise unittest.SkipTest('C compiler unavailable')
        cls.temporary = tempfile.TemporaryDirectory()
        cls.library = Path(cls.temporary.name) / 'libevents.so'
        fixture = Path(__file__).resolve().parents[1] / 'fixtures/qgf_ffi_abi_contract.c'
        subprocess.run([compiler, '-std=c11', '-shared', '-fPIC', str(fixture), '-o', str(cls.library)],
                       check=True, capture_output=True, text=True)
        cls.probe = ctypes.CDLL(str(cls.library))
        for symbol in ('qgf_event_size', 'qgf_event_alignment', 'qgf_event_type_offset'):
            getattr(cls.probe, symbol).restype = ctypes.c_size_t
        cls.contract = NativeOutputABIContract(
            cls.probe.qgf_event_size(), cls.probe.qgf_event_alignment(),
            (('type', cls.probe.qgf_event_type_offset()),),
        )

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_event_from_real_c_via_vm_is_typed_by_external_adapter(self):
        vm = QRVM()
        vm.bind_native({}, NativeLibrary(self.library),
                       output_layouts={'qgf_poll_event': self.contract.opaque_storage('VerifiedEvent')},
                       output_success_statuses={'qgf_poll_event': (1,)},
                       output_empty_statuses={'qgf_poll_event': (0,)})
        vm.execute([(OpCode.CALL, ('qgf_poll_event', 0))], {})
        event = decode_sdl_event(vm.stack[-1], self.contract)
        self.assertIsInstance(event, SDLEventSnapshot)
        self.assertEqual(event.type, 0x100)
        self.assertEqual(len(event.raw), self.contract.size)

    def test_empty_queue_is_none(self):
        self.assertIsNone(decode_sdl_event(None, self.contract))

    def test_truncated_payload_is_rejected(self):
        with self.assertRaises(NativeABIContractError):
            decode_sdl_event(bytes(self.contract.size - 1), self.contract)

    def test_missing_verified_type_offset_is_rejected(self):
        contract = NativeOutputABIContract(self.contract.size, self.contract.alignment, ())
        with self.assertRaises(NativeABIContractError):
            decode_sdl_event(bytes(contract.size), contract)

    def test_missing_contract_is_rejected(self):
        with self.assertRaises(NativeABIContractError):
            decode_sdl_event(bytes(self.contract.size), None)


if __name__ == '__main__':
    unittest.main()
