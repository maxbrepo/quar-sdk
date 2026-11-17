"""Chapter 43: opt-in scoped cleanup for native handles."""
from __future__ import annotations

import unittest

from tests.test_ch43_cycle_a_lifetime import NativeLifecycleCycleATests
from qrvm.native_ffi import NativeFFIError, NativeSignature


class NativeManagedScopeTests(NativeLifecycleCycleATests):
    def test_scope_releases_after_normal_exit(self):
        before = self.counter.native_destroyed()
        with self.library.managed_handle(self.create, self.destroy) as handle:
            self.assertEqual(self.library.call(self.read, handle), 42)
        self.assertEqual(self.counter.native_destroyed(), before + 1)
        with self.assertRaisesRegex(NativeFFIError, 'released'):
            self.library.call(self.read, handle)

    def test_scope_releases_when_body_raises(self):
        before = self.counter.native_destroyed()
        with self.assertRaisesRegex(RuntimeError, 'body failure'):
            with self.library.managed_handle(self.create, self.destroy) as handle:
                raise RuntimeError('body failure')
        self.assertEqual(self.counter.native_destroyed(), before + 1)
        with self.assertRaisesRegex(NativeFFIError, 'released'):
            self.library.call(self.read, handle)

    def test_scope_rejects_nonopaque_creator_without_calling_it(self):
        before = self.counter.native_created()
        with self.assertRaisesRegex(NativeFFIError, 'creator'):
            with self.library.managed_handle(self.read, self.destroy):
                pass
        self.assertEqual(self.counter.native_created(), before)

    def test_scope_rejects_invalid_destructor_before_creating(self):
        before = self.counter.native_created()
        with self.assertRaisesRegex(NativeFFIError, 'destructor'):
            with self.library.managed_handle(self.create, self.read):
                pass
        self.assertEqual(self.counter.native_created(), before)

    def test_explicit_release_inside_scope_does_not_double_destroy(self):
        before = self.counter.native_destroyed()
        with self.library.managed_handle(self.create, self.destroy) as handle:
            self.library.release_handle(handle, self.destroy)
        self.assertEqual(self.counter.native_destroyed(), before + 1)

    def test_alias_release_inside_scope_does_not_double_destroy(self):
        before = self.counter.native_destroyed()
        with self.library.managed_handle(self.create, self.destroy) as handle:
            alias = self.library.call(self.create)
            self.assertEqual(alias.address, handle.address)
            self.library.release_handle(alias, self.destroy)
        self.assertEqual(self.counter.native_destroyed(), before + 1)

    def test_body_exception_after_manual_release_is_preserved(self):
        before = self.counter.native_destroyed()
        with self.assertRaisesRegex(ValueError, 'original failure'):
            with self.library.managed_handle(self.create, self.destroy) as handle:
                self.library.release_handle(handle, self.destroy)
                raise ValueError('original failure')
        self.assertEqual(self.counter.native_destroyed(), before + 1)

    def test_scope_revokes_aliases_on_exit(self):
        with self.library.managed_handle(self.create, self.destroy) as handle:
            alias = self.library.call(self.create)
            self.assertEqual(alias.address, handle.address)
        with self.assertRaisesRegex(NativeFFIError, 'released'):
            self.library.call(self.read, alias)


if __name__ == '__main__':
    unittest.main()
