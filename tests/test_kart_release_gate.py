"""Release-gate checks for Kart 0.0.1 local package management."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from kart.core import KartError, installed_packages, update_local, verify_lock


class KartReleaseGateTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.app = self.root / "app"
        self.lib = self.root / "lib"
        self.app.mkdir()
        self.lib.mkdir()
        (self.app / "kart.toml").write_text(
            '[package]\nname = "app"\nversion = "1.0.0"\n'
            '[dependencies]\nlib = { path = "../lib" }\n', encoding="utf-8"
        )
        (self.lib / "kart.toml").write_text(
            '[package]\nname = "lib"\nversion = "1.0.0"\n', encoding="utf-8"
        )
        (self.lib / "math.vq").write_text(
            "int add(int a, int b) { return a + b; }\n", encoding="utf-8"
        )

    def test_clean_install_is_consistent(self):
        update_local(self.app, self.root / "store")
        verify_lock(self.app)
        self.assertEqual(set(installed_packages(self.app)), {"lib"})

    def test_relocation_keeps_lock_valid(self):
        update_local(self.app, self.root / "store")
        shutil.copytree(self.root / "app", self.root / "moved" / "app")
        shutil.copytree(self.root / "lib", self.root / "moved" / "lib")
        verify_lock(self.root / "moved" / "app")

    def test_missing_dependency_after_relocation_is_rejected(self):
        update_local(self.app, self.root / "store")
        shutil.copytree(self.root / "app", self.root / "isolated" / "app")
        with self.assertRaises(KartError):
            verify_lock(self.root / "isolated" / "app")

    def test_installed_package_tampering_is_rejected(self):
        update_local(self.app, self.root / "store")
        (self.app / ".kart/packages/lib/math.vq").write_text("tampered")
        with self.assertRaises(KartError):
            installed_packages(self.app)

    def test_stale_backup_blocks_update(self):
        update_local(self.app, self.root / "store")
        (self.app / ".kart/.install-backup").mkdir()
        with self.assertRaisesRegex(KartError, "Unsafe or incomplete prior installation"):
            update_local(self.app, self.root / "store")
