"""Verify opt-in typed decoding of native composite output in QRVM."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from qrvm.native_ffi import NativeLibrary
from qrvm.native_composite_layout import NativeArrayType, NativeCompositeLayout
from qrvm.native_composite_decode import NativeCompositeDecodeError
from qrvm.vm import QRVM
from qrvm.instructions import OpCode


class VMOutputDecodeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        fixture = Path(__file__).resolve().parents[1] / 'fixtures/qgf_ffi_composite_out.c'
        cls.lib = Path(cls.tmp.name) / 'libpacket.so'
        subprocess.run(['cc', '-std=c11', '-shared', '-fPIC', str(fixture), '-o', str(cls.lib)], check=True, capture_output=True)
        point = NativeCompositeLayout('OutPoint', 'struct', (('x', 'i32'), ('y', 'f64')))
        number = NativeCompositeLayout('OutNumber', 'union', (('bits', 'u64'), ('value', 'f64')))
        cls.layout = NativeCompositeLayout('OutPacket', 'struct', (('tag', 'u32'), ('points', NativeArrayType(point, 3)), ('number', number), ('samples', NativeArrayType('i32', 4))))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_output(self, selections=None):
        vm = QRVM()
        options = {'output_layouts': {'qgf_fill_packet': self.layout}}
        if selections is not None:
            options['output_union_members'] = {'qgf_fill_packet': selections}
        vm.bind_native({}, NativeLibrary(self.lib), **options)
        variables = {}
        vm.execute([(OpCode.CALL, ('qgf_fill_packet', 0)), (OpCode.STORE, 'result')], variables)
        return variables['result']

    def test_typed_composite_result(self):
        result = self.run_output({'OutPacket.number': 'bits'})
        self.assertEqual(result['tag'], 42)
        self.assertEqual(result['points'][0]['x'], 7)
        self.assertEqual(result['number']['bits'], 0x1122334455667788)

    def test_default_raw_bytes_unchanged(self):
        self.assertIsInstance(self.run_output(), bytes)

    def test_union_selection_required(self):
        with self.assertRaises(NativeCompositeDecodeError):
            self.run_output({})

    def test_invalid_union_selection_rejected(self):
        with self.assertRaises(NativeCompositeDecodeError):
            self.run_output({'OutPacket.number': 'missing'})

    def test_unknown_output_binding_rejected(self):
        vm = QRVM()
        with self.assertRaises(ValueError):
            vm.bind_native({}, NativeLibrary(self.lib), output_union_members={'missing': {}})


if __name__ == '__main__':
    unittest.main()
