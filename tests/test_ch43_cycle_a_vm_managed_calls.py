"""Chapter 43: opt-in native resource cleanup around QRVM execution."""
from __future__ import annotations

from unittest.mock import patch

from frontend.quar.qir.program_lowering import lower_ast_program
from main import build_frontend
from qrvm.native_ffi import NativeFFIError, NativeSignature
from qrvm.qir_program_backend import compile_qir_program
from qrvm.vm import QRVM
from tests.test_ch43_cycle_a_lifetime import NativeLifecycleCycleATests


class VMManagedCallsTests(NativeLifecycleCycleATests):
    def _package(self, body: str):
        source = ('extern "C" opaque native_create(); '
                  'extern "C" i32 native_read(opaque item); '
                  'extern "C" void native_destroy(opaque item); ' + body)
        ast, _ = build_frontend(source)
        return compile_qir_program(lower_ast_program(ast))

    def _run(self, body: str):
        package = self._package(body)
        vm = QRVM()
        vm.bind_native(package['native_declarations'], self.library,
                       release_symbols=('native_destroy',))
        with self.library.managed_calls({'native_create': self.destroy}):
            vm.run(package)

    def test_vm_normal_exit_releases_unreleased_resource(self):
        before = self.counter.native_destroyed()
        self._run('opaque item = native_create(); i32 value = native_read(item);')
        self.assertEqual(self.counter.native_destroyed(), before + 1)

    def test_vm_explicit_release_is_not_repeated(self):
        before = self.counter.native_destroyed()
        self._run('opaque item = native_create(); native_destroy(item);')
        self.assertEqual(self.counter.native_destroyed(), before + 1)

    def test_vm_exception_releases_resource(self):
        before = self.counter.native_destroyed()
        with self.assertRaises(NativeFFIError):
            self._run('opaque item = native_create(); native_destroy(item); i32 value = native_read(item);')
        self.assertEqual(self.counter.native_destroyed(), before + 1)

    def test_multiple_resources_are_released_once_per_address(self):
        # The fixture intentionally returns aliases to one static address.
        before = self.counter.native_destroyed()
        self._run('opaque first = native_create(); opaque second = native_create();')
        self.assertEqual(self.counter.native_destroyed(), before + 1)

    def test_reject_invalid_cleanup_mapping(self):
        with self.assertRaisesRegex(NativeFFIError, 'destructor'):
            with self.library.managed_calls({'native_create': self.read}):
                pass

    def test_body_error_preserved_if_cleanup_fails(self):
        with patch.object(self.library, 'release_handle', side_effect=NativeFFIError('cleanup failed')):
            with self.assertRaisesRegex(ValueError, 'body failed') as result:
                with self.library.managed_calls({'native_create': self.destroy}):
                    self.library.call(self.create)
                    raise ValueError('body failed')
        self.assertIsInstance(result.exception.__cause__, NativeFFIError)

    def test_nested_scopes_do_not_duplicate_cleanup(self):
        before = self.counter.native_destroyed()
        with self.library.managed_calls({'native_create': self.destroy}):
            with self.library.managed_calls({'native_create': self.destroy}):
                self.library.call(self.create)
        self.assertEqual(self.counter.native_destroyed(), before + 1)
