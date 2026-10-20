"""Regression tests for installed package index validation."""
import tempfile
import unittest
from pathlib import Path
from kart.core import KartError, installed_packages, update_local

class KartInstallAuditTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.app = root / "app"
        lib = root / "lib"
        self.app.mkdir()
        lib.mkdir()
        (self.app / "kart.toml").write_text(
            '[package]\nname = "app"\nversion = "1.0.0"\n'
            '[dependencies]\nlib = { path = "../lib" }\n')
        (lib / "kart.toml").write_text(
            '[package]\nname = "lib"\nversion = "1.0.0"\n')
        update_local(self.app, root / "cache")

    def test_valid_installation(self):
        self.assertEqual(set(installed_packages(self.app)), {"lib"})

    def test_unindexed_directory_rejected(self):
        (self.app / ".kart/packages/extra").mkdir()
        with self.assertRaisesRegex(KartError, "Unexpected or missing"):
            installed_packages(self.app)

    def test_unindexed_file_rejected(self):
        (self.app / ".kart/packages/unexpected.txt").write_text("unexpected")
        with self.assertRaisesRegex(KartError, "Unexpected or missing"):
            installed_packages(self.app)

    def test_packages_symlink_rejected(self):
        target = self.app / ".kart/packages"
        original = self.app / ".kart/old-packages"
        target.rename(original)
        target.symlink_to(original, target_is_directory=True)
        with self.assertRaisesRegex(KartError, "Unsafe or missing"):
            installed_packages(self.app)
