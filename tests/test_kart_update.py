"""Regression tests for local update and read-only status."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kart.core import KartError, project_status, update_local, installed_packages


class KartUpdateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.app = self.root / 'app'
        self.lib = self.root / 'lib'
        self.app.mkdir()
        self.lib.mkdir()
        (self.app / 'kart.toml').write_text('[package]\nname = "app"\nversion = "1.0.0"\n[dependencies]\nlib = {path = "../lib", version = ">=1.0.0"}\n')
        (self.lib / 'kart.toml').write_text('[package]\nname = "lib"\nversion = "1.0.0"\n')
        (self.lib / 'math.vq').write_text('original')
        self.store = self.root / 'store'

    def test_status_is_read_only(self):
        stages = project_status(self.app)
        self.assertEqual([name for name, _, _ in stages], ['manifest', 'resolution', 'lockfile', 'installation'])
        self.assertFalse((self.app / 'kart.lock').exists())
        self.assertFalse((self.app / '.kart').exists())

    def test_update_creates_lock_and_installation(self):
        update_local(self.app, self.store)
        self.assertTrue((self.app / 'kart.lock').exists())
        self.assertIn('lib', installed_packages(self.app))

    def test_update_refreshes_modified_source(self):
        update_local(self.app, self.store)
        (self.lib / 'math.vq').write_text('changed')
        update_local(self.app, self.store)
        self.assertEqual((self.app / '.kart/packages/lib/math.vq').read_text(), 'changed')

    def test_invalid_dependency_preserves_previous_state(self):
        update_local(self.app, self.store)
        original = (self.app / 'kart.lock').read_bytes()
        (self.lib / 'kart.toml').write_text('[package]\nname = "lib"\nversion = "0.1.0"\n')
        with self.assertRaises(KartError):
            update_local(self.app, self.store)
        self.assertEqual((self.app / 'kart.lock').read_bytes(), original)

    def test_install_failure_rolls_back_lock(self):
        update_local(self.app, self.store)
        original = (self.app / 'kart.lock').read_bytes()
        (self.lib / 'math.vq').write_text('updated')
        with patch('kart.core.install_packages', side_effect=KartError('simulated')):
            with self.assertRaises(KartError):
                update_local(self.app, self.store)
        self.assertEqual((self.app / 'kart.lock').read_bytes(), original)

    def test_rejects_symlink_lock(self):
        outside = self.root / 'outside'
        outside.write_text('untouched')
        (self.app / 'kart.lock').symlink_to(outside)
        with self.assertRaises(KartError):
            update_local(self.app, self.store)
        self.assertEqual(outside.read_text(), 'untouched')

    def test_stale_backup_blocks_update(self):
        install_root = self.app / '.kart'
        (install_root / '.install-backup').mkdir(parents=True)
        with self.assertRaises(KartError):
            update_local(self.app, self.store)
        self.assertFalse((self.app / 'kart.lock').exists())
