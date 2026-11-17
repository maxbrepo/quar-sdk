"""Run a real .vq source file through the existing C output ABI pipeline."""
import ctypes
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from bindings.sdl2_events import decode_sdl_keyboard_event
from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from frontend.quar.semantic import SemanticAnalyzer
from qrvm.compiler import QRVMCompiler
from qrvm.native_abi_contract import NativeOutputABIContract
from qrvm.native_composite_layout import NativeCompositeLayout
from qrvm.native_ffi import NativeLibrary
from qrvm.vm import QRVM

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'examples/0.0.5/typed/24_interoperability/24_69_qgf_keyboard_native_output.vq'
FIXTURE = ROOT / 'fixtures/qgf_ffi_keyboard_event.c'


class QGFNativeSourceTests(unittest.TestCase):
    def test_example_is_real_source_with_explicit_abi(self):
        source = SOURCE.read_text(encoding='utf-8')
        self.assertIn('extern "C"', source)
        self.assertIn('out QgfKeyboardEvent', source)
        ast = Parser(Lexer(source).tokenize()).parse()
        SemanticAnalyzer().analyze(ast)
        package = QRVMCompiler().compile(ast)
        self.assertIn('QgfKeyboardEvent', package['native_struct_layouts'])

    @unittest.skipUnless(shutil.which('cc'), 'C compiler unavailable')
    def test_vq_source_to_native_c_and_back_to_qrvm(self):
        source = SOURCE.read_text(encoding='utf-8')
        ast = Parser(Lexer(source).tokenize()).parse()
        SemanticAnalyzer().analyze(ast)
        package = QRVMCompiler().compile(ast)
        with tempfile.TemporaryDirectory() as folder:
            library = Path(folder) / 'libevents.so'
            subprocess.run(['cc', '-std=c11', '-shared', '-fPIC', str(FIXTURE), '-o', str(library)],
                           check=True, capture_output=True, text=True)
            probe = ctypes.CDLL(str(library))
            for key in ('size', 'alignment', 'type_offset', 'scancode_offset', 'sym_offset'):
                getattr(probe, 'qgf_keyboard_' + key).restype = ctypes.c_size_t
            contract = NativeOutputABIContract(
                probe.qgf_keyboard_size(), probe.qgf_keyboard_alignment(),
                (('type', probe.qgf_keyboard_type_offset()),
                 ('key_scancode', probe.qgf_keyboard_scancode_offset()),
                 ('key_sym', probe.qgf_keyboard_sym_offset())))
            layout = NativeCompositeLayout('QgfKeyboardEvent', 'struct',
                                           tuple(package['native_struct_layouts']['QgfKeyboardEvent']))
            self.assertEqual(layout.describe()['size'], contract.size)
            self.assertEqual(layout.describe()['alignment'], contract.alignment)
            vm = QRVM()
            vm.bind_native({}, NativeLibrary(library),
                           output_layouts={'qgf_poll_keyboard': layout},
                           declared_output_layouts={'qgf_poll_keyboard': layout},
                           output_success_statuses={'qgf_poll_keyboard': (1,)},
                           output_empty_statuses={'qgf_poll_keyboard': (0,)})
            variables = {}
            vm.execute(package['instructions'], variables)
            event = decode_sdl_keyboard_event(variables['result'], contract)
            self.assertEqual((event.type, event.scancode, event.keycode), (0x300, 4, -42))


if __name__ == '__main__':
    unittest.main()
