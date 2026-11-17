"""Chapter 43: cleanup failures must not conceal application failures."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from tests.test_ch43_cycle_a_lifetime import NativeLifecycleCycleATests
from qrvm.native_ffi import NativeFFIError


class NativeCleanupErrorTests(NativeLifecycleCycleATests):
    def test_cleanup_failure_after_body_error_preserves_both(self):
        with patch.object(self.library, "release_handle", side_effect=NativeFFIError("cleanup failed")):
            with self.assertRaisesRegex(ValueError, "application failed") as captured:
                with self.library.managed_handle(self.create, self.destroy):
                    raise ValueError("application failed")
        self.assertIsInstance(captured.exception.__cause__, NativeFFIError)
        self.assertIn("cleanup failed", str(captured.exception.__cause__))
        self.assertTrue(any("cleanup failed" in note for note in captured.exception.__notes__))

    def test_cleanup_failure_on_normal_exit_is_reported(self):
        with patch.object(self.library, "release_handle", side_effect=NativeFFIError("cleanup failed")):
            with self.assertRaisesRegex(NativeFFIError, "cleanup failed"):
                with self.library.managed_handle(self.create, self.destroy):
                    pass

    def test_body_error_with_successful_cleanup_is_preserved(self):
        before = self.counter.native_destroyed()
        with self.assertRaisesRegex(ValueError, "application failed"):
            with self.library.managed_handle(self.create, self.destroy):
                raise ValueError("application failed")
        self.assertEqual(self.counter.native_destroyed(), before + 1)

    def test_manual_release_with_body_error_does_not_cleanup_twice(self):
        before = self.counter.native_destroyed()
        with self.assertRaisesRegex(ValueError, "application failed"):
            with self.library.managed_handle(self.create, self.destroy) as handle:
                self.library.release_handle(handle, self.destroy)
                raise ValueError("application failed")
        self.assertEqual(self.counter.native_destroyed(), before + 1)


if __name__ == "__main__":
    unittest.main()
