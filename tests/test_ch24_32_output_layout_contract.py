"""Reject silent ABI layout substitution in trusted native output bindings."""
import unittest
from qrvm.vm import QRVM
from qrvm.native_composite_layout import NativeCompositeLayout, NativeArrayType


class NativeOutputLayoutContractTests(unittest.TestCase):
    def setUp(self):
        self.source = NativeCompositeLayout('Event', 'struct', (('type', 'u64'),))
        self.runtime = NativeCompositeLayout('Event', 'struct', (('words', NativeArrayType('u64', 32)),))
        self.library = object()  # Binding validation does not call the library.

    def test_reject_silent_sdl_event_buffer_substitution(self):
        with self.assertRaisesRegex(ValueError, 'ABI layout mismatch'):
            QRVM().bind_native({}, self.library, output_layouts={'SDL_PollEvent': self.runtime},
                               declared_output_layouts={'SDL_PollEvent': self.source})

    def test_accept_matching_declared_layout(self):
        vm = QRVM()
        vm.bind_native({}, self.library, output_layouts={'read_event': self.source},
                       declared_output_layouts={'read_event': self.source})
        self.assertIn('read_event', vm.native_output_functions)

    def test_reject_undeclared_output_binding(self):
        with self.assertRaisesRegex(ValueError, 'matching native output bindings'):
            QRVM().bind_native({}, self.library, declared_output_layouts={'missing': self.source})

    def test_reject_non_layout_declaration(self):
        with self.assertRaisesRegex(ValueError, 'Invalid declared output layout'):
            QRVM().bind_native({}, self.library, output_layouts={'read_event': self.source},
                               declared_output_layouts={'read_event': 'Event'})


if __name__ == '__main__':
    unittest.main()
