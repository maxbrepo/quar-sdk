"""Chapter 43: conservative alias invalidation after explicit release."""
from __future__ import annotations

from dataclasses import replace
import unittest

from tests.test_ch43_cycle_a_lifetime import NativeLifecycleCycleATests
from qrvm.native_ffi import NativeFFIError, NativeLibrary, NativeSignature


class NativeAliasTests(NativeLifecycleCycleATests):
    """Reuse the compiled C fixture and its native counters."""

    def test_two_handles_same_address_are_revoked_together(self):
        first = self.library.call(self.create)
        second = self.library.call(self.create)
        self.assertEqual(first.address, second.address)
        self.assertNotEqual(first.token, second.token)
        self.library.release_handle(first, self.destroy)
        with self.assertRaisesRegex(NativeFFIError, 'released'):
            self.library.call(self.read, second)
        with self.assertRaisesRegex(NativeFFIError, 'released'):
            self.library.release_handle(second, self.destroy)

    def test_invalid_destructor_does_not_revoke_alias(self):
        first = self.library.call(self.create)
        second = self.library.call(self.create)
        with self.assertRaisesRegex(NativeFFIError, 'destructor'):
            self.library.release_handle(first, self.read)
        self.assertEqual(self.library.call(self.read, second), 42)
        self.library.release_handle(first, self.destroy)

    def test_forged_alias_does_not_revoke_valid_token(self):
        first = self.library.call(self.create)
        with self.assertRaisesRegex(NativeFFIError, 'registered'):
            self.library.release_handle(replace(first, token=999999), self.destroy)
        self.assertEqual(self.library.call(self.read, first), 42)
        self.library.release_handle(first, self.destroy)


if __name__ == '__main__':
    unittest.main()
