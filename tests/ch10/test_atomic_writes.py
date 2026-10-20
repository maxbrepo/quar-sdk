"""Chapter 10: regression tests for opt-in atomic file replacement.

Run from the SDK root with: python -m unittest discover -s tests/ch10 -v
"""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from frontend.quar.semantic import SemanticAnalyzer, SemanticError
from qrvm.compiler import QRVMCompiler
from qrvm.vm import QRVM
from qrvm.io_errors import IOErrorKind, QuarIOError


def execute(source: str) -> str:
    """Run a Visual Quar program and return the printed text."""
    tree = Parser(Lexer(source).tokenize()).parse()
    program = QRVMCompiler().compile(SemanticAnalyzer().analyze(tree))
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        QRVM().run(program)
    return out.getvalue().strip()


class AtomicWritesTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.target = self.root / "test.bin"

    def source(self, method, value):
        return f'File.{method}("{self.target.as_posix()}", {value});'

    def assert_no_staged_files(self):
        self.assertEqual(sorted(p.name for p in self.root.glob("*.vqtmp")), [])

    def test_binary_replacement_and_readback(self):
        self.target.write_bytes(b"previous")
        execute(self.source("write_bytes_atomic", 'Bytes.from_hex("00ff80")'))
        self.assertEqual(self.target.read_bytes(), bytes.fromhex("00ff80"))
        self.assert_no_staged_files()

    def test_utf8_text_replacement(self):
        self.target.write_text("previous")
        execute(self.source("write_text_atomic", '"Caffè"'))
        self.assertEqual(self.target.read_bytes(), "Caffè".encode("utf-8"))
        self.assert_no_staged_files()

    def test_new_file(self):
        execute(self.source("write_bytes_atomic", 'Bytes.from_hex("0102")'))
        self.assertEqual(self.target.read_bytes(), b"\x01\x02")
        self.assert_no_staged_files()

    def test_replace_failure_preserves_old_file(self):
        self.target.write_bytes(b"previous")
        with patch("qrvm.atomic_io.os.replace", side_effect=OSError("simulated replace failure")):
            with self.assertRaises(QuarIOError) as exc:
                execute(self.source("write_bytes_atomic", 'Bytes.from_hex("ffff")'))
        self.assertEqual(exc.exception.kind, IOErrorKind.OTHER)
        self.assertEqual(self.target.read_bytes(), b"previous")
        self.assert_no_staged_files()

    def test_sync_failure_preserves_old_file(self):
        self.target.write_bytes(b"previous")
        with patch("qrvm.atomic_io.os.fsync", side_effect=OSError("simulated fsync failure")):
            with self.assertRaises(QuarIOError):
                execute(self.source("write_bytes_atomic", 'Bytes.from_hex("ffff")'))
        self.assertEqual(self.target.read_bytes(), b"previous")
        self.assert_no_staged_files()

    def test_missing_parent_does_not_create_target(self):
        self.target = self.root / "missing" / "target.bin"
        with self.assertRaises(QuarIOError) as exc:
            execute(self.source("write_bytes_atomic", 'Bytes.from_hex("0a")'))
        self.assertEqual(exc.exception.kind, IOErrorKind.NOT_FOUND)
        self.assertFalse(self.target.exists())

    def test_unicode_path_and_spaces(self):
        self.target = self.root / "file café prova.txt"
        execute(self.source("write_text_atomic", '"Testo valido"'))
        self.assertEqual(self.target.read_text(encoding="utf-8"), "Testo valido")
        self.assert_no_staged_files()

    def test_empty_file_replacement(self):
        self.target.write_bytes(b"previous")
        execute(self.source("write_bytes_atomic", 'Bytes.from_hex("")'))
        self.assertEqual(self.target.read_bytes(), b"")
        self.assert_no_staged_files()

    def test_destination_is_directory_preserves_directory(self):
        self.target.mkdir()
        with self.assertRaises(QuarIOError):
            execute(self.source("write_bytes_atomic", 'Bytes.from_hex("aa")'))
        self.assertTrue(self.target.is_dir())
        self.assert_no_staged_files()

    def test_short_write_preserves_old_file(self):
        self.target.write_bytes(b"previous")
        import os
        original_fdopen = os.fdopen

        class ShortWriteStream:
            def __init__(self, stream):
                self.stream = stream

            def __enter__(self):
                self.stream.__enter__()
                return self

            def __exit__(self, *args):
                return self.stream.__exit__(*args)

            def write(self, content):
                return self.stream.write(content[:1])

        def short_fdopen(*args, **kwargs):
            return ShortWriteStream(original_fdopen(*args, **kwargs))

        with patch("qrvm.atomic_io.os.fdopen", side_effect=short_fdopen):
            with self.assertRaises(QuarIOError):
                execute(self.source("write_bytes_atomic", 'Bytes.from_hex("ffee")'))
        self.assertEqual(self.target.read_bytes(), b"previous")
        self.assert_no_staged_files()

    def test_wrong_type_rejected_at_compile_time(self):
        with self.assertRaises(SemanticError):
            execute(self.source("write_bytes_atomic", '"not bytes"'))
        with self.assertRaises(SemanticError):
            execute(self.source("write_text_atomic", 'Bytes.from_hex("aa")'))


if __name__ == "__main__":
    unittest.main()

class AtomicMetadataTest(unittest.TestCase):
    def test_existing_permissions_are_preserved(self):
        import os
        import stat
        if os.name != "posix":
            self.skipTest("POSIX permission semantics")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "restricted.bin"
            path.write_bytes(b"old")
            path.chmod(0o640)
            from qrvm.atomic_io import write_bytes_atomic
            write_bytes_atomic(path, b"new")
            self.assertEqual(path.read_bytes(), b"new")
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o640)

    def test_symlink_is_not_replaced(self):
        import os
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "target"
            link = Path(directory) / "link"
            target.write_bytes(b"original")
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")
            from qrvm.atomic_io import write_bytes_atomic
            with self.assertRaises(OSError):
                write_bytes_atomic(link, b"replacement")
            self.assertTrue(link.is_symlink())
            self.assertEqual(target.read_bytes(), b"original")


class AtomicDurabilityTest(unittest.TestCase):
    def test_directory_sync_attempted_after_replace(self):
        from qrvm.atomic_io import write_bytes_atomic
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "target"
            with patch("qrvm.atomic_io._sync_parent_directory_best_effort", return_value=True) as sync:
                write_bytes_atomic(target, b"updated")
            sync.assert_called_once_with(target.parent)
            self.assertEqual(target.read_bytes(), b"updated")

    def test_directory_sync_failure_does_not_misreport_replacement_failure(self):
        from qrvm.atomic_io import write_bytes_atomic
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "target"
            target.write_bytes(b"old")
            with patch("qrvm.atomic_io.os.fsync", side_effect=[None, OSError("unsupported directory sync")]):
                write_bytes_atomic(target, b"new")
            self.assertEqual(target.read_bytes(), b"new")

class AtomicPortabilityContractTest(unittest.TestCase):
    """Exercise platform branches without claiming tests on other operating systems."""

    def test_non_posix_skips_directory_sync(self):
        from qrvm.atomic_io import _sync_parent_directory_best_effort
        with patch("qrvm.atomic_io.os.name", "nt"):
            with patch("qrvm.atomic_io.os.open") as open_mock:
                self.assertFalse(_sync_parent_directory_best_effort(Path(".")))
                open_mock.assert_not_called()

    def test_unavailable_directory_flag_skips_sync(self):
        from qrvm.atomic_io import _sync_parent_directory_best_effort
        with patch("qrvm.atomic_io.os.name", "posix"):
            with patch("qrvm.atomic_io.os.O_DIRECTORY", None, create=True):
                # An unsupported flag must not be used in a system call.
                # This test exposes the distinction between absent and null flags.
                with patch("qrvm.atomic_io.os.open") as open_mock:
                    try:
                        result = _sync_parent_directory_best_effort(Path("."))
                    except TypeError:
                        self.fail("Null O_DIRECTORY flag was not handled")
                    self.assertFalse(result)
                    open_mock.assert_not_called()

    def test_directory_open_failure_is_best_effort(self):
        from qrvm.atomic_io import _sync_parent_directory_best_effort
        if not hasattr(__import__("os"), "O_DIRECTORY"):
            self.skipTest("No directory-open flag on this platform")
        with patch("qrvm.atomic_io.os.open", side_effect=OSError("unsupported")):
            self.assertFalse(_sync_parent_directory_best_effort(Path(".")))

    def test_new_file_permissions_not_world_readable_on_posix(self):
        import os
        import stat
        if os.name != "posix":
            self.skipTest("POSIX permissions")
        from qrvm.atomic_io import write_bytes_atomic
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "created"
            write_bytes_atomic(target, b"data")
            self.assertEqual(stat.S_IMODE(target.stat().st_mode) & 0o077, 0)
