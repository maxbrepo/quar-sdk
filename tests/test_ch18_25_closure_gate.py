"""Chapter 18 closure gate: observable QBC runtime contract."""
import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from qrvm.qbc_cli import cached_compile, compile_file, main, run_file
from qrvm.bytecode_serialization import QBCError, read_qbc


class Chapter18ClosureGate(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.source = self.directory / 'main.vq'
        self.source.write_text('print(17);\n', encoding='utf-8')

    def test_compiled_program_runs_without_source(self):
        artifact = self.directory / 'main.qbc'
        compile_file(self.source, artifact)
        self.source.unlink()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            run_file(artifact)
        self.assertEqual(output.getvalue(), '17\n')

    def test_cache_reuses_unchanged_source(self):
        cache = self.directory / 'cache'
        first, first_hit = cached_compile(self.source, cache)
        second, second_hit = cached_compile(self.source, cache)
        self.assertFalse(first_hit)
        self.assertTrue(second_hit)
        self.assertEqual(first, second)

    def test_cache_invalidates_after_source_change(self):
        cache = self.directory / 'cache'
        artifact, _ = cached_compile(self.source, cache)
        self.source.write_text('print(18);\n', encoding='utf-8')
        second, hit = cached_compile(self.source, cache)
        self.assertEqual(artifact, second)
        self.assertFalse(hit)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            run_file(second)
        self.assertEqual(output.getvalue(), '18\n')

    def test_corrupt_qbc_is_rejected(self):
        artifact = self.directory / 'main.qbc'
        compile_file(self.source, artifact)
        contents = bytearray(artifact.read_bytes())
        contents[-1] ^= 1
        artifact.write_bytes(contents)
        with self.assertRaises(QBCError):
            read_qbc(artifact)

    def test_cli_compile_and_run(self):
        artifact = self.directory / 'main.qbc'
        self.assertEqual(main(['compile', str(self.source), '-o', str(artifact)]), 0)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(['run', str(artifact)]), 0)
        self.assertEqual(output.getvalue(), '17\n')


if __name__ == '__main__':
    unittest.main()
