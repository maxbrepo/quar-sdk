"""Visual Quar source to native output to typed event, without SDL in QRVM."""
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


class SourceTypedEventTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('cc'):
            raise unittest.SkipTest('C compiler unavailable')
        cls.folder = tempfile.TemporaryDirectory()
        cls.library = Path(cls.folder.name) / 'libevents.so'
        fixture = Path(__file__).resolve().parents[1] / 'fixtures/qgf_ffi_keyboard_event.c'
        subprocess.run(['cc', '-std=c11', '-shared', '-fPIC', str(fixture), '-o', str(cls.library)],
                       check=True, capture_output=True, text=True)
        probe = ctypes.CDLL(str(cls.library))
        for key in ('size', 'alignment', 'type_offset', 'scancode_offset', 'sym_offset'):
            getattr(probe, 'qgf_keyboard_' + key).restype = ctypes.c_size_t
        cls.contract = NativeOutputABIContract(
            probe.qgf_keyboard_size(), probe.qgf_keyboard_alignment(),
            (('type', probe.qgf_keyboard_type_offset()),
             ('key_scancode', probe.qgf_keyboard_scancode_offset()),
             ('key_sym', probe.qgf_keyboard_sym_offset())),
        )

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def test_source_to_typed_keyboard_event_with_verified_layout(self):
        source = '''extern "C" struct QgfKeyboardEvent {
            u32 type; i32 scancode; i32 sym; u32 reserved; u64 payload;
        };
        extern "C" i32 qgf_poll_keyboard(out QgfKeyboardEvent event);
        bytes result = qgf_poll_keyboard();'''
        ast = Parser(Lexer(source).tokenize()).parse()
        SemanticAnalyzer().analyze(ast)
        package = QRVMCompiler().compile(ast)
        layout = NativeCompositeLayout('QgfKeyboardEvent', 'struct',
                                       tuple(package['native_struct_layouts']['QgfKeyboardEvent']))
        self.assertEqual(layout.describe()['size'], self.contract.size)
        self.assertEqual(layout.describe()['alignment'], self.contract.alignment)
        vm = QRVM()
        vm.bind_native({}, NativeLibrary(self.library),
                       output_layouts={'qgf_poll_keyboard': layout},
                       declared_output_layouts={'qgf_poll_keyboard': layout},
                       output_success_statuses={'qgf_poll_keyboard': (1,)},
                       output_empty_statuses={'qgf_poll_keyboard': (0,)})
        variables = {}
        vm.execute(package['instructions'], variables)
        event = decode_sdl_keyboard_event(variables['result'], self.contract)
        self.assertEqual((event.type, event.scancode, event.keycode), (0x300, 4, -42))


if __name__ == '__main__':
    unittest.main()
