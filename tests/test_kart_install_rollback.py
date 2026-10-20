"""Fault-injection tests for package installation replacement and recovery."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kart.core import KartError, install_packages, update_local


class KartInstallRollbackTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.app = self.root / "app"
        self.lib = self.root / "lib"
        self.app.mkdir()
        self.lib.mkdir()
        (self.app / "kart.toml").write_text(
            '[package]\nname="app"\nversion="1.0.0"\n'
            '[dependencies]\nlib={path="../lib"}\n')
        (self.lib / "kart.toml").write_text(
            '[package]\nname="lib"\nversion="1.0.0"\n')
        (self.lib / "math.vq").write_text("before")
        self.store = self.root / "store"
        update_local(self.app, self.store)
        self.lock_before = (self.app / "kart.lock").read_bytes()
        (self.lib / "math.vq").write_text("after")

    def test_replacement_failure_restores_install_and_lock(self):
        original_rename = Path.rename
        def fail_stage_index(path, target):
            if path.name == "installed.json" and ".install-stage-" in str(path):
                raise OSError("injected index replacement failure")
            return original_rename(path, target)
        with patch.object(Path, "rename", autospec=True, side_effect=fail_stage_index):
            with self.assertRaises(KartError):
                update_local(self.app, self.store)
        self.assertEqual((self.app / ".kart/packages/lib/math.vq").read_text(), "before")
        self.assertEqual((self.app / "kart.lock").read_bytes(), self.lock_before)
        self.assertFalse((self.app / ".kart/.install-backup").exists())

    def test_failed_rollback_preserves_backup(self):
        original_rename = Path.rename
        def fail_replacement_and_restore(path, target):
            if path.name == "installed.json" and ".install-stage-" in str(path):
                raise OSError("injected replacement failure")
            if ".install-backup" in str(path):
                raise OSError("injected rollback failure")
            return original_rename(path, target)
        with patch.object(Path, "rename", autospec=True, side_effect=fail_replacement_and_restore):
            with self.assertRaisesRegex(KartError, "rollback failed"):
                update_local(self.app, self.store)
        self.assertTrue((self.app / ".kart/.install-backup").is_dir())
        self.assertTrue((self.app / ".kart/.install-backup/installed.json").exists())
        with self.assertRaises(KartError):
            update_local(self.app, self.store)

    def test_successful_update_removes_backup(self):
        update_local(self.app, self.store)
        self.assertEqual((self.app / ".kart/packages/lib/math.vq").read_text(), "after")
        self.assertFalse((self.app / ".kart/.install-backup").exists())
