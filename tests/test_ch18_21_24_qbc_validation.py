"""Final QBC cache and portable execution validation tests."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from qrvm.qbc_cli import cached_compile, compile_file, main, run_file
from qrvm.bytecode_serialization import QBCError, read_qbc


class QBCFinalValidationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.source = self.root / 'sample.vq'
        self.source.write_text('print(42);\n', encoding='utf-8')
        self.cache = self.root / 'cache'

    def _tamper(self, update):
        artifact, _ = cached_compile(self.source, self.cache)
        manifest_path = next(self.cache.glob('*.json'))
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        update(manifest)
        manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
        return artifact

    def test_empty_dependencies_cannot_claim_hit(self):
        artifact = self._tamper(lambda m: m.update(dependencies={}))
        self.assertEqual(cached_compile(self.source, self.cache), (artifact, False))

    def test_missing_source_dependency_cannot_claim_hit(self):
        artifact = self._tamper(lambda m: m.update(dependencies={'other': '0' * 64}))
        self.assertEqual(cached_compile(self.source, self.cache), (artifact, False))

    def test_malformed_dependency_digest_cannot_claim_hit(self):
        artifact = self._tamper(lambda m: m['dependencies'].update({str(self.source.resolve()): 12}))
        self.assertEqual(cached_compile(self.source, self.cache), (artifact, False))

    def test_malformed_dependency_container_cannot_claim_hit(self):
        artifact = self._tamper(lambda m: m.update(dependencies=[]))
        self.assertEqual(cached_compile(self.source, self.cache), (artifact, False))

    def test_valid_manifest_still_hits(self):
        artifact, hit = cached_compile(self.source, self.cache)
        self.assertFalse(hit)
        self.assertEqual(cached_compile(self.source, self.cache), (artifact, True))

    def test_qbc_without_source_remains_runnable(self):
        artifact = self.root / 'sample.qbc'
        compile_file(self.source, artifact)
        self.source.unlink()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            run_file(artifact)
        self.assertEqual(output.getvalue().strip(), '42')

    def test_qbc_truncation_rejected(self):
        artifact = self.root / 'sample.qbc'
        compile_file(self.source, artifact)
        artifact.write_bytes(artifact.read_bytes()[:-1])
        with self.assertRaises(QBCError):
            read_qbc(artifact)

    def test_cli_run_without_source(self):
        artifact = self.root / 'sample.qbc'
        compile_file(self.source, artifact)
        self.source.unlink()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(['run', str(artifact)]), 0)
        self.assertEqual(output.getvalue().strip(), '42')


if __name__ == '__main__':
    unittest.main()
