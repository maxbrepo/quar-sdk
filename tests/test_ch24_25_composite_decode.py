"""Check safe decoding of copied composite ABI output."""
import ctypes
import subprocess
import tempfile
import unittest
from pathlib import Path
from qrvm.native_composite_layout import NativeArrayType, NativeCompositeLayout
from qrvm.native_composite_decode import decode_composite, NativeCompositeDecodeError
from qrvm.native_ffi import NativeLibrary


class CompositeDecodeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        root = Path(__file__).resolve().parents[1]
        cls.library_path = Path(cls.folder.name) / 'libpacket.so'
        subprocess.run(['cc', '-std=c11', '-shared', '-fPIC', str(root / 'fixtures/qgf_ffi_composite_out.c'), '-o', str(cls.library_path)], check=True, capture_output=True)
        point = NativeCompositeLayout('OutPoint', 'struct', (('x', 'i32'), ('y', 'f64')))
        number = NativeCompositeLayout('OutNumber', 'union', (('bits', 'u64'), ('value', 'f64')))
        cls.layout = NativeCompositeLayout('OutPacket', 'struct', (('tag', 'u32'), ('points', NativeArrayType(point, 3)), ('number', number), ('samples', NativeArrayType('i32', 4))))
        _, cls.raw = NativeLibrary(cls.library_path).call_composite_out('qgf_fill_packet', cls.layout)

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def test_decodes_nested_fields_and_array(self):
        result = decode_composite(self.raw, self.layout, union_members={'OutPacket.number': 'bits'})
        self.assertEqual(result['tag'], 42)
        self.assertEqual(result['points'][0], {'x': 7, 'y': 2.5})
        self.assertEqual(result['number']['bits'], 0x1122334455667788)
        self.assertEqual(result['samples'][0], -3)

    def test_union_requires_explicit_selection(self):
        with self.assertRaisesRegex(NativeCompositeDecodeError, 'Explicit union member'):
            decode_composite(self.raw, self.layout)

    def test_wrong_member_rejected(self):
        with self.assertRaises(NativeCompositeDecodeError):
            decode_composite(self.raw, self.layout, union_members={'OutPacket.number': 'unknown'})

    def test_unused_selection_rejected(self):
        with self.assertRaisesRegex(NativeCompositeDecodeError, 'unused'):
            decode_composite(self.raw, self.layout, union_members={'OutPacket.number': 'bits', 'missing': 'x'})

    def test_size_mismatch_rejected(self):
        with self.assertRaisesRegex(NativeCompositeDecodeError, 'size'):
            decode_composite(self.raw[:-1], self.layout, union_members={'OutPacket.number': 'bits'})

    def test_mutable_buffer_rejected(self):
        with self.assertRaises(NativeCompositeDecodeError):
            decode_composite(bytearray(self.raw), self.layout, union_members={'OutPacket.number': 'bits'})


if __name__ == '__main__':
    unittest.main()
