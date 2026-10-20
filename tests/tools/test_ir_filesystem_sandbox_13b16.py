"""Filesystem parity tests use an isolated root for each QRVM execution."""
import os
import tempfile
import unittest
from pathlib import Path

from tools.ir_runtime_audit import audit_runtime_file


@unittest.skipUnless(hasattr(os, 'chroot') and os.geteuid() == 0, 'chroot requires root')
class IRFilesystemSandboxTests(unittest.TestCase):
    def test_file_write_and_read_are_equivalent(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'test.vq'
            source.write_text('File.write_text("sample.txt", "hello"); print(File.read_text("sample.txt"));', encoding='utf-8')
            self.assertEqual(audit_runtime_file(source)[0], 'runtime_equal')
            self.assertFalse((Path(folder) / 'sample.txt').exists())

    def test_absolute_paths_do_not_escape_sandbox(self):
        with tempfile.TemporaryDirectory() as folder:
            sentinel = Path(folder) / 'sentinel.txt'
            sentinel.write_text('untouched', encoding='utf-8')
            source = Path(folder) / 'test.vq'
            source.write_text(f'File.write_text("{sentinel}", "changed");', encoding='utf-8')
            # The sandbox lacks the external parent directory: both routes
            # must fail equivalently, without touching the real sentinel.
            self.assertEqual(audit_runtime_file(source)[0], 'runtime_equal')
            self.assertEqual(sentinel.read_text(encoding='utf-8'), 'untouched')


if __name__ == '__main__':
    unittest.main()
