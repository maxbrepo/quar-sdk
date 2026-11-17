"""Verify generic native output states: data, empty, and failure."""
import subprocess
import tempfile
import unittest
from pathlib import Path

from qrvm.instructions import OpCode
from qrvm.native_composite_layout import NativeCompositeLayout
from qrvm.native_ffi import NativeFFIError, NativeLibrary
from qrvm.vm import QRVM


class EmptyOutputStatusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        fixture = Path(__file__).resolve().parents[1] / 'fixtures/qgf_ffi_struct_out.c'
        cls.path = Path(cls.temp.name) / 'libstatus.so'
        subprocess.run(['cc', '-std=c11', '-shared', '-fPIC', str(fixture), '-o', str(cls.path)], check=True, capture_output=True)
        cls.layout = NativeCompositeLayout('Point', 'struct', (('x', 'i32'), ('y', 'f64'), ('flags', 'u32')))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_call(self, symbol, **options):
        vm = QRVM()
        vm.bind_native({}, NativeLibrary(self.path), output_layouts={symbol: self.layout}, **options)
        vm.execute([(OpCode.CALL, (symbol, 0))], {})
        return vm.stack.pop()

    def test_data_status_returns_bytes(self):
        self.assertIs(type(self.run_call('qgf_fill_point', output_empty_statuses={'qgf_fill_point': (7,)})), bytes)

    def test_empty_status_returns_none_without_exposing_buffer(self):
        self.assertIsNone(self.run_call('qgf_fail_point', output_empty_statuses={'qgf_fail_point': (7,)}))

    def test_unclassified_status_is_error(self):
        with self.assertRaises(NativeFFIError):
            self.run_call('qgf_fail_point', output_empty_statuses={'qgf_fail_point': (1,)})

    def test_default_behavior_is_unchanged(self):
        with self.assertRaises(NativeFFIError):
            self.run_call('qgf_fail_point')

    def test_overlapping_policies_are_rejected(self):
        with self.assertRaises(ValueError):
            self.run_call('qgf_fill_point', output_empty_statuses={'qgf_fill_point': (0,)})

    def test_unknown_empty_policy_is_rejected(self):
        vm = QRVM()
        with self.assertRaises(ValueError):
            vm.bind_native({}, NativeLibrary(self.path), output_layouts={}, output_empty_statuses={'unknown': (7,)})

    def test_invalid_empty_policies_are_rejected(self):
        for statuses in ([7], (True,), (7, 7), ('7',)):
            with self.subTest(statuses=statuses), self.assertRaises(ValueError):
                self.run_call('qgf_fill_point', output_empty_statuses={'qgf_fill_point': statuses})


if __name__ == '__main__':
    unittest.main()
