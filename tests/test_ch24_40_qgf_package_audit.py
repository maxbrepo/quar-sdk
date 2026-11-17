"""Regression tests for release completeness, rather than just runtime behavior."""
import hashlib
from pathlib import Path
import tempfile
import unittest
import zipfile

from tooling.ch24_qgf_package_audit import (
    REQUIRED_FILES, REQUIRED_EXPORTS, ReleaseAuditError, audit_archive,
)

ROOT = Path(__file__).resolve().parents[1]


def make_zip(archive_path, *, excluded=(), overrides=None):
    """Produce a test archive from the working SDK with a complete manifest."""
    overrides = overrides or {}
    payload = {}
    for filename in REQUIRED_FILES:
        if filename not in excluded:
            payload[filename] = overrides.get(filename, (ROOT / filename).read_bytes())
    payload['README_24_40.txt'] = b'Chapter 24 release audit fixture\n'
    sums = ''.join(
        f'{hashlib.sha256(data).hexdigest()}  {name}\n'
        for name, data in sorted(payload.items())
    ).encode('utf-8')
    with zipfile.ZipFile(archive_path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in payload.items():
            archive.writestr(name, data)
        archive.writestr('SHA256SUMS_24_40.txt', sums)


class QGFPackageAuditTests(unittest.TestCase):
    def test_required_sources_exist_and_export_expected_symbols(self):
        for filename in REQUIRED_FILES:
            with self.subTest(file=filename):
                self.assertTrue((ROOT / filename).is_file())
        for filename, exports in REQUIRED_EXPORTS.items():
            import ast
            tree = ast.parse((ROOT / filename).read_text(encoding='utf-8'))
            present = {node.name for node in tree.body if isinstance(node, (ast.ClassDef, ast.FunctionDef))}
            self.assertTrue(set(exports) <= present)

    def test_complete_release_passes_audit(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'complete.zip'
            make_zip(path)
            count, _ = audit_archive(path)
            self.assertGreaterEqual(count, len(REQUIRED_FILES))

    def test_missing_binding_module_is_detected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'incomplete.zip'
            make_zip(path, excluded={'bindings/sdl2_events.py'})
            with self.assertRaisesRegex(ReleaseAuditError, 'Missing package dependency'):
                audit_archive(path)

    def test_missing_poller_export_is_detected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'old-binding.zip'
            source = (ROOT / 'bindings/sdl2_events.py').read_text(encoding='utf-8')
            source = source.replace('class SDLEventPoller:', 'class LegacyEventPoller:')
            make_zip(path, overrides={'bindings/sdl2_events.py': source.encode('utf-8')})
            with self.assertRaisesRegex(ReleaseAuditError, 'Missing exported symbol'):
                audit_archive(path)

    def test_corrupted_payload_is_detected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'corrupt.zip'
            make_zip(path)
            with zipfile.ZipFile(path) as archive:
                data = {name: archive.read(name) for name in archive.namelist()}
            data['bindings/__init__.py'] += b'changed\n'
            with zipfile.ZipFile(path, 'w') as archive:
                for name, contents in data.items():
                    archive.writestr(name, contents)
            with self.assertRaisesRegex(ReleaseAuditError, 'SHA-256 mismatch'):
                audit_archive(path)


if __name__ == '__main__':
    unittest.main()
