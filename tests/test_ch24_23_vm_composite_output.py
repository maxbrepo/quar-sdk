"""Exercise explicit VM dispatch to adapter-owned composite output buffers."""
import subprocess
import tempfile
import unittest
from pathlib import Path

from qrvm.instructions import OpCode
from qrvm.native_composite_layout import NativeArrayType, NativeCompositeLayout
from qrvm.native_ffi import NativeFFIError, NativeLibrary
from qrvm.vm import QRVM


class NativeVMCompositeOutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        source = Path(__file__).resolve().parents[1] / 'fixtures/qgf_ffi_composite_out.c'
        cls.library_path = Path(cls.folder.name) / 'libcomposite_out.so'
        subprocess.run(['cc', '-std=c11', '-shared', '-fPIC', str(source), '-o', str(cls.library_path)], check=True, capture_output=True)
        point = NativeCompositeLayout('OutPoint', 'struct', (('x', 'i32'), ('y', 'f64')))
        number = NativeCompositeLayout('OutNumber', 'union', (('bits', 'u64'), ('value', 'f64')))
        cls.layout = NativeCompositeLayout('OutPacket', 'struct', (('tag', 'u32'), ('points', NativeArrayType(point, 3)), ('number', number), ('samples', NativeArrayType('i32', 4))))

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def make_vm(self, symbols=None):
        vm = QRVM()
        vm.bind_native({}, NativeLibrary(self.library_path), output_layouts=symbols or {'qgf_fill_packet': self.layout})
        return vm

    def test_vm_output_is_immutable_and_correct(self):
        vm = self.make_vm()
        vm.execute([(OpCode.CALL, ('qgf_fill_packet', 0))], {})
        raw = vm.stack.pop()
        self.assertIs(type(raw), bytes)
        packet = self.layout.ctypes_type().from_buffer_copy(raw)
        self.assertEqual(packet.tag, 42)
        self.assertEqual(packet.points[0].x, 7)

    def test_vm_rejects_source_arguments(self):
        vm = self.make_vm()
        with self.assertRaisesRegex(RuntimeError, 'zero source arguments'):
            vm.execute([(OpCode.CALL, ('qgf_fill_packet', 1))], {})

    def test_vm_propagates_native_failure(self):
        vm = self.make_vm({'qgf_fail_packet': self.layout})
        with self.assertRaisesRegex(NativeFFIError, 'status 7'):
            vm.execute([(OpCode.CALL, ('qgf_fail_packet', 0))], {})

    def test_invalid_layout_rejected_at_binding(self):
        vm = QRVM()
        with self.assertRaises(ValueError):
            vm.bind_native({}, NativeLibrary(self.library_path), output_layouts={'qgf_fill_packet': 'i32'})

    def test_conflicting_native_binding_rejected(self):
        vm = QRVM()
        with self.assertRaises(ValueError):
            vm.bind_native({'qgf_fill_packet': ((), 'i32')}, NativeLibrary(self.library_path), output_layouts={'qgf_fill_packet': self.layout})


if __name__ == '__main__':
    unittest.main()
