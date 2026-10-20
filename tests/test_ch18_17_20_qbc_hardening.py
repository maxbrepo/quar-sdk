"""Regression tests for QBC CLI compatibility and cache integrity."""
import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from qrvm.qbc_cli import cached_compile, compile_file, main
from qrvm.bytecode_serialization import read_qbc


class QBCHardeningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'demo.vq'
        self.source.write_text('print(42);\n', encoding='utf-8')

    def test_cached_artifact_digest_recorded(self):
        artifact, hit = cached_compile(self.source, self.root / 'cache')
        self.assertFalse(hit)
        manifest = json.loads(next((self.root / 'cache').glob('*.json')).read_text())
        self.assertEqual(manifest['artifact_sha256'], hashlib.sha256(artifact.read_bytes()).hexdigest())

    def test_manifest_digest_tampering_forces_rebuild(self):
        artifact, _ = cached_compile(self.source, self.root / 'cache')
        manifest_path = next((self.root / 'cache').glob('*.json'))
        manifest = json.loads(manifest_path.read_text())
        manifest['artifact_sha256'] = '0' * 64
        manifest_path.write_text(json.dumps(manifest))
        self.assertEqual(cached_compile(self.source, self.root / 'cache'), (artifact, False))

    def test_cached_run_executes_source(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(['cached-run', str(self.source), '--cache-dir', str(self.root / 'cache')]), 0)
        self.assertEqual(output.getvalue().strip(), '42')

    def test_compile_failure_preserves_existing_artifact(self):
        artifact = self.root / 'demo.qbc'
        compile_file(self.source, artifact)
        before = artifact.read_bytes()
        self.source.write_text('this is not valid source !!!\n', encoding='utf-8')
        with self.assertRaises(Exception):
            compile_file(self.source, artifact)
        self.assertEqual(artifact.read_bytes(), before)
        read_qbc(artifact)

    def test_compile_does_not_leave_temp_files(self):
        artifact = self.root / 'demo.qbc'
        compile_file(self.source, artifact)
        self.assertFalse((self.root / 'demo.qbc.tmp').exists())

    def test_run_rejects_corrupt_bytecode(self):
        artifact = self.root / 'demo.qbc'
        artifact.write_bytes(b'not a bytecode file')
        with contextlib.redirect_stderr(io.StringIO()) as errors:
            self.assertEqual(main(['run', str(artifact)]), 1)
        self.assertIn('QBC error:', errors.getvalue())


if __name__ == '__main__':
    unittest.main()
