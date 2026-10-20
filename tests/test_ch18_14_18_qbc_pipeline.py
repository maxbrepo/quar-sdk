"""End-to-end tests for QBC compilation, execution and content cache."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from qrvm.qbc_cli import cached_compile, compile_file, main, run_file
from qrvm.bytecode_serialization import read_qbc


class QBCRuntimePipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'hello.vq'
        self.source.write_text('print(42);\n', encoding='utf-8')
        self.qbc = self.root / 'hello.qbc'

    def test_compile_and_run(self):
        compile_file(self.source, self.qbc)
        self.assertTrue(self.qbc.is_file())
        read_qbc(self.qbc)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            run_file(self.qbc)
        self.assertEqual(output.getvalue().strip(), '42')

    def test_cli_compile_run(self):
        self.assertEqual(main(['compile', str(self.source), '-o', str(self.qbc)]), 0)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(['run', str(self.qbc)]), 0)
        self.assertEqual(output.getvalue().strip(), '42')

    def test_cache_hit_and_source_change(self):
        cache = self.root / 'cache'
        artifact, hit = cached_compile(self.source, cache)
        self.assertFalse(hit)
        self.assertTrue(artifact.exists())
        self.assertEqual(cached_compile(self.source, cache), (artifact, True))
        self.source.write_text('print(43);\n', encoding='utf-8')
        self.assertEqual(cached_compile(self.source, cache), (artifact, False))
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            run_file(artifact)
        self.assertEqual(output.getvalue().strip(), '43')

    def test_corrupt_cache_rebuilt(self):
        cache = self.root / 'cache'
        artifact, _ = cached_compile(self.source, cache)
        artifact.write_bytes(b'bad')
        self.assertFalse(cached_compile(self.source, cache)[1])
        read_qbc(artifact)

    def test_missing_qbc_returns_failure(self):
        error = io.StringIO()
        with contextlib.redirect_stderr(error):
            self.assertEqual(main(['run', str(self.root / 'missing.qbc')]), 1)
        self.assertIn('QBC error:', error.getvalue())

    def test_cache_manifest_records_source(self):
        cache = self.root / 'cache'
        cached_compile(self.source, cache)
        manifest = json.loads(next(cache.glob('*.json')).read_text())
        self.assertEqual(manifest['dependencies'][str(self.source.resolve())],
                         __import__('hashlib').sha256(self.source.read_bytes()).hexdigest())
        self.assertEqual(len(manifest['compiler']), 64)


if __name__ == '__main__':
    unittest.main()
