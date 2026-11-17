"""Chapter 43 cycle A: native cleanup contract and failure-path regressions."""
from __future__ import annotations

import ctypes
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from qrvm.native_ffi import NativeFFIError, NativeLibrary, NativeSignature


SOURCE = r'''
#include <stdint.h>
static int objects[3] = {11, 22, 33};
static int next_object = 0;
static int releases[3] = {0, 0, 0};
static int release_order[3] = {0, 0, 0};
static int release_total = 0;
void *create_object(void) {
    if (next_object == 3) return 0;
    return &objects[next_object++];
}
void destroy_object(void *ptr) {
    for (int i = 0; i < 3; ++i) {
        if (ptr == &objects[i]) {
            releases[i]++;
            release_order[release_total++] = i;
            return;
        }
    }
}
int release_count(int index) { return releases[index]; }
int release_position(int index) { return release_order[index]; }
int release_total_count(void) { return release_total; }
'''


class CleanupContractTests(unittest.TestCase):
    def setUp(self):
        compiler = shutil.which('cc') or shutil.which('gcc')
        if compiler is None:
            self.skipTest('C compiler unavailable')
        self.temp = tempfile.TemporaryDirectory()
        source = Path(self.temp.name) / 'contract.c'
        library_path = Path(self.temp.name) / 'libcontract.so'
        source.write_text(SOURCE, encoding='utf-8')
        subprocess.run([compiler, '-shared', '-fPIC', '-o', str(library_path), str(source)],
                       check=True, capture_output=True, text=True)
        self.library = NativeLibrary(library_path)
        self.raw = ctypes.CDLL(str(library_path))
        for name in ('release_count', 'release_position'):
            getattr(self.raw, name).argtypes = (ctypes.c_int,)
            getattr(self.raw, name).restype = ctypes.c_int
        self.raw.release_total_count.restype = ctypes.c_int
        self.creator = NativeSignature('create_object', (), 'opaque')
        self.destroyer = NativeSignature('destroy_object', ('opaque',), 'void')

    def tearDown(self):
        if hasattr(self, 'temp'):
            self.temp.cleanup()

    def test_reverse_order_cleanup(self):
        with self.library.managed_calls({'create_object': self.destroyer}):
            handles = [self.library.call(self.creator) for _ in range(3)]
            self.assertEqual(self.raw.release_total_count(), 0)
        self.assertEqual([self.raw.release_position(i) for i in range(3)], [2, 1, 0])
        for handle in handles:
            with self.assertRaisesRegex(NativeFFIError, 'released'):
                self.library.release_handle(handle, self.destroyer)

    def test_explicit_release_skips_only_released_handle(self):
        with self.library.managed_calls({'create_object': self.destroyer}):
            first = self.library.call(self.creator)
            second = self.library.call(self.creator)
            self.library.release_handle(first, self.destroyer)
        self.assertEqual(self.raw.release_total_count(), 2)
        self.assertEqual(self.raw.release_count(0), 1)
        self.assertEqual(self.raw.release_count(1), 1)
        with self.assertRaisesRegex(NativeFFIError, 'released'):
            self.library.release_handle(second, self.destroyer)

    def test_exception_releases_all_in_reverse_order(self):
        with self.assertRaisesRegex(RuntimeError, 'application failure'):
            with self.library.managed_calls({'create_object': self.destroyer}):
                for _ in range(3):
                    self.library.call(self.creator)
                raise RuntimeError('application failure')
        self.assertEqual([self.raw.release_position(i) for i in range(3)], [2, 1, 0])

    def test_cleanup_continues_after_first_destructor_failure(self):
        original = self.library.release_handle
        attempts = []

        def flaky(handle, signature):
            attempts.append(handle)
            if len(attempts) == 1:
                raise NativeFFIError('simulated destructor failure')
            return original(handle, signature)

        with patch.object(self.library, 'release_handle', side_effect=flaky):
            with self.assertRaisesRegex(NativeFFIError, 'simulated destructor failure'):
                with self.library.managed_calls({'create_object': self.destroyer}):
                    for _ in range(3):
                        self.library.call(self.creator)
        self.assertEqual(len(attempts), 3)
        self.assertEqual(self.raw.release_total_count(), 2)

    def test_multiple_cleanup_failures_are_grouped(self):
        with patch.object(self.library, 'release_handle', side_effect=NativeFFIError('failed')):
            with self.assertRaises(ExceptionGroup) as captured:
                with self.library.managed_calls({'create_object': self.destroyer}):
                    self.library.call(self.creator)
                    self.library.call(self.creator)
        self.assertEqual(len(captured.exception.exceptions), 2)

    def test_body_error_survives_multiple_cleanup_failures(self):
        with patch.object(self.library, 'release_handle', side_effect=NativeFFIError('failed')):
            with self.assertRaisesRegex(ValueError, 'original') as captured:
                with self.library.managed_calls({'create_object': self.destroyer}):
                    self.library.call(self.creator)
                    self.library.call(self.creator)
                    raise ValueError('original')
        self.assertIsInstance(captured.exception.__cause__, NativeFFIError)
        self.assertEqual(len(captured.exception.__notes__), 2)


if __name__ == '__main__':
    unittest.main()
