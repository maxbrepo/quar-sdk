"""Chapter 10 bytes, directory enumeration, and file-handle lifetime tests."""

import builtins
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
    """Run a Visual Quar source and return its exact stdout."""
    tree = Parser(Lexer(source).tokenize()).parse()
    checked = SemanticAnalyzer().analyze(tree)
    program = QRVMCompiler().compile(checked)
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        QRVM().run(program)
    return stream.getvalue()


class BytesAndDirectoryTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def test_bytes_round_trip_and_append(self):
        path = (self.root / "binary.dat").as_posix()
        output = execute(
            f'File.write_bytes("{path}", Bytes.from_hex("00ff10")); '
            f'File.append_bytes("{path}", Bytes.from_hex("ab")); '
            f'print(Bytes.to_hex(File.read_bytes("{path}"))); '
            f'print(Bytes.length(File.read_bytes("{path}")));'
        )
        self.assertEqual(output, "00ff10ab\n4\n")
        self.assertEqual((self.root / "binary.dat").read_bytes(), bytes.fromhex("00ff10ab"))

    def test_bytes_indexing_and_comparison(self):
        output = execute(
            'bytes a = Bytes.from_hex("00ff10"); '
            'bytes b = Bytes.from_hex("00ff10"); '
            'bytes c = Bytes.from_hex("00ff11"); '
            'print(a[0]); print(a[1]); print(a[2]); '
            'print(a == b); print(a != c);'
        )
        self.assertEqual(output, "0\n255\n16\nTrue\nTrue\n")

    def test_invalid_bytes_indexes(self):
        for index in (-1, 2):
            with self.subTest(index=index):
                with self.assertRaisesRegex(RuntimeError, "index out of bounds"):
                    execute(f'bytes data = Bytes.from_hex("00ff"); print(data[{index}]);')

    def test_invalid_hex_data(self):
        with self.assertRaises(QuarIOError) as raised:
            execute('print(Bytes.to_hex(Bytes.from_hex("gg")));')
        self.assertEqual(raised.exception.kind, IOErrorKind.INVALID_DATA)

    def test_directory_entries_and_types(self):
        (self.root / "b").mkdir()
        (self.root / "a.txt").write_text("data", encoding="utf-8")
        path = self.root.as_posix()
        output = execute(
            f'print(Directory.entry("{path}", 0)); '
            f'print(Directory.entry_is_file("{path}", 0)); '
            f'print(Directory.entry_is_directory("{path}", 1));'
        )
        self.assertEqual(output, "a.txt\nTrue\nTrue\n")
        with self.assertRaises(QuarIOError) as raised:
            execute(f'print(Directory.entry("{path}", 7));')
        self.assertEqual(raised.exception.kind, IOErrorKind.INVALID_DATA)

    def test_binary_handles_close_and_check_types(self):
        path = (self.root / "sample.bin").as_posix()
        handles = []
        original_open = builtins.open

        def tracking_open(*args, **kwargs):
            handle = original_open(*args, **kwargs)
            handles.append(handle)
            return handle

        source = (
            f'with File.open("{path}", "wb") as handle {{ '
            'handle.write(Bytes.from_hex("00ff10")); } '
            f'with File.open("{path}", "rb") as handle {{ '
            'bytes data = handle.read_all(); print(Bytes.to_hex(data)); }'
        )
        with patch("builtins.open", side_effect=tracking_open):
            self.assertEqual(execute(source), "00ff10\n")
        self.assertEqual(len(handles), 2)
        self.assertTrue(all(handle.closed for handle in handles))
        with self.assertRaises(SemanticError):
            execute(f'with File.open("{path}", "wb") as handle {{ handle.write("wrong"); }}')


class ResourceCleanupTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "sample.txt"
        self.path.write_text("hello", encoding="utf-8")

    def assert_handles_closed(self, source: str, exception_type=None, count=1):
        """Track actual Python file descriptors through VM execution."""
        handles = []
        original_open = builtins.open

        def tracking_open(*args, **kwargs):
            handle = original_open(*args, **kwargs)
            handles.append(handle)
            return handle

        with patch("builtins.open", side_effect=tracking_open):
            if exception_type:
                with self.assertRaises(exception_type):
                    execute(source)
            else:
                execute(source)
        self.assertEqual(len(handles), count)
        self.assertTrue(all(handle.closed for handle in handles))

    def test_normal_exit(self):
        self.assert_handles_closed(
            f'with File.open("{self.path.as_posix()}", "r") as f {{ print(f.read_all()); }}'
        )

    def test_exception_closes_handle(self):
        self.assert_handles_closed(
            f'with File.open("{self.path.as_posix()}", "r") as f {{ int x = 1 / 0; }}',
            RuntimeError,
        )

    def test_nested_exception_closes_all_handles(self):
        self.assert_handles_closed(
            f'with File.open("{self.path.as_posix()}", "r") as a {{ '
            f'with File.open("{self.path.as_posix()}", "r") as b {{ int x = 1 / 0; }} }}',
            RuntimeError,
            count=2,
        )

    def test_early_return_closes_handle(self):
        self.assert_handles_closed(
            f'i32 run() {{ with File.open("{self.path.as_posix()}", "w") as f {{ '
            'f.write("data"); return 7; } } print(run());'
        )

    def test_write_failure_closes_handle(self):
        original_open = builtins.open
        handles = []

        class FailWrite:
            def __init__(self, real):
                self.real = real
            def __enter__(self):
                return self
            def __exit__(self, *args):
                self.real.close()
            @property
            def closed(self):
                return self.real.closed
            def write(self, _):
                raise OSError("simulated write failure")

        def failing_open(*args, **kwargs):
            wrapper = FailWrite(original_open(*args, **kwargs))
            handles.append(wrapper)
            return wrapper

        with patch("builtins.open", side_effect=failing_open):
            with self.assertRaises(QuarIOError) as raised:
                execute(f'with File.open("{self.path.as_posix()}", "w") as f {{ f.write("data"); }}')
        self.assertEqual(raised.exception.kind, IOErrorKind.OTHER)
        self.assertEqual(len(handles), 1)
        self.assertTrue(handles[0].closed)


if __name__ == "__main__":
    unittest.main()
