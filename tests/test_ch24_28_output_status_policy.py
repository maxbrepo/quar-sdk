"""Check per-symbol output status policies without SDL-specific VM logic."""
import subprocess
import tempfile
import unittest
from pathlib import Path

from qrvm.instructions import OpCode
from qrvm.native_composite_layout import NativeCompositeLayout
from qrvm.native_ffi import NativeFFIError, NativeLibrary
from qrvm.vm import QRVM


class OutputStatusPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        fixture = Path(__file__).resolve().parents[1] / 'fixtures/qgf_ffi_struct_out.c'
        cls.library_path = Path(cls.temp.name) / 'libstatus.so'
        subprocess.run(['cc', '-std=c11', '-shared', '-fPIC', str(fixture), '-o', str(cls.library_path)], check=True, capture_output=True)
        cls.layout = NativeCompositeLayout('Point', 'struct', (('x', 'i32'), ('y', 'f64'), ('flags', 'u32')))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_symbol(self, name, policy=None):
        vm = QRVM()
        kwargs = {} if policy is None else {'output_success_statuses': {name: policy}}
        vm.bind_native({}, NativeLibrary(self.library_path), output_layouts={name: self.layout}, **kwargs)
        vm.execute([(OpCode.CALL, (name, 0))], {})
        return vm.stack.pop()

    def test_default_zero_success(self):
        self.assertIs(type(self.run_symbol('qgf_fill_point')), bytes)

    def test_default_nonzero_failure(self):
        with self.assertRaisesRegex(NativeFFIError, 'status 7'):
            self.run_symbol('qgf_fail_point')

    def test_configured_nonzero_success(self):
        self.assertIs(type(self.run_symbol('qgf_fail_point', (7,))), bytes)

    def test_configured_nonzero_rejects_zero(self):
        with self.assertRaisesRegex(NativeFFIError, 'status 0'):
            self.run_symbol('qgf_fill_point', (1,))

    def test_reject_unknown_policy(self):
        vm = QRVM()
        with self.assertRaises(ValueError):
            vm.bind_native({}, NativeLibrary(self.library_path), output_layouts={}, output_success_statuses={'missing': (1,)})

    def test_reject_invalid_policy(self):
        for policy in ((), (True,), (1, 1), [1], ('1',)):
            with self.subTest(policy=policy), self.assertRaises(ValueError):
                vm = QRVM()
                vm.bind_native({}, NativeLibrary(self.library_path), output_layouts={'qgf_fill_point': self.layout}, output_success_statuses={'qgf_fill_point': policy})


if __name__ == '__main__':
    unittest.main()
