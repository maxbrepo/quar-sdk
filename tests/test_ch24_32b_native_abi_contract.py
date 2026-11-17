"""Use compiled-C measurements to gate opaque native output buffers."""
import ctypes
import shutil
import subprocess
import tempfile
from pathlib import Path
import unittest

from qrvm.native_abi_contract import NativeABIContractError, NativeOutputABIContract
from qrvm.native_ffi import NativeLibrary
from qrvm.vm import QRVM


class NativeABIContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = shutil.which('cc')
        if not compiler:
            raise unittest.SkipTest('C compiler unavailable')
        cls.temp = tempfile.TemporaryDirectory()
        cls.library_path = Path(cls.temp.name) / 'libprobe.so'
        source = Path(__file__).resolve().parents[1] / 'fixtures/qgf_ffi_abi_contract.c'
        subprocess.run([compiler, '-std=c11', '-shared', '-fPIC', str(source), '-o', str(cls.library_path)],
                       capture_output=True, text=True, check=True)
        cls.c = ctypes.CDLL(str(cls.library_path))
        for symbol in ('qgf_event_size', 'qgf_event_alignment', 'qgf_event_type_offset', 'qgf_event_code_offset'):
            getattr(cls.c, symbol).restype = ctypes.c_size_t
        cls.contract = NativeOutputABIContract(
            cls.c.qgf_event_size(), cls.c.qgf_event_alignment(),
            (('type', cls.c.qgf_event_type_offset()), ('code', cls.c.qgf_event_code_offset())),
        )

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_probe_drives_exact_storage(self):
        layout = self.contract.opaque_storage('QgfEventStorage')
        self.assertEqual(layout.describe()['size'], self.contract.size)
        self.assertEqual(layout.describe()['alignment'], self.contract.alignment)

    def test_actual_c_output_through_vm(self):
        layout = self.contract.opaque_storage('QgfEventStorage')
        vm = QRVM()
        vm.bind_native({}, NativeLibrary(self.library_path), output_layouts={'qgf_poll_event': layout},
                       output_success_statuses={'qgf_poll_event': (1,)},
                       output_empty_statuses={'qgf_poll_event': (0,)})
        from qrvm.instructions import OpCode
        # Use existing CALL bytecode to exercise the real C -> FFI -> QRVM path.
        vm.execute([(OpCode.CALL, ('qgf_poll_event', 0))], {})
        raw = vm.stack[-1]
        self.assertEqual(self.contract.read_u32(raw, 'type'), 0x100)
        self.assertEqual(self.contract.read_u32(raw, 'code'), 42)

    def test_reject_bad_dimensions_and_unknown_fields(self):
        for size, alignment in ((0, 8), (7, 8), (16, 16)):
            with self.subTest(size=size, alignment=alignment), self.assertRaises(NativeABIContractError):
                NativeOutputABIContract(size, alignment, ())
        with self.assertRaises(NativeABIContractError):
            self.contract.read_u32(bytes(self.contract.size), 'unknown')

    def test_reject_unverified_buffer_size(self):
        with self.assertRaises(NativeABIContractError):
            self.contract.read_u32(b'\x00' * 8, 'type')

    def test_reject_bad_offsets(self):
        with self.assertRaises(NativeABIContractError):
            NativeOutputABIContract(32, 8, (('type', 0), ('type', 4)))


if __name__ == '__main__':
    unittest.main()
