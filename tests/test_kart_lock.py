"""Kart lockfile consistency tests."""
import json
import tempfile
import unittest
from pathlib import Path

from kart.core import KartError, verify_lock, write_lock


class KartLockTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.lib = self.root / "lib"
        self.lib.mkdir()
        (self.root / "kart.toml").write_text(
            '[package]\nname = "app"\nversion = "0.0.1"\n'
            '[dependencies]\nlib = { path = "lib" }\n', encoding="utf-8"
        )
        (self.lib / "kart.toml").write_text(
            '[package]\nname = "lib"\nversion = "1.0.0"\n', encoding="utf-8"
        )

    def test_valid_lock(self):
        write_lock(self.root)
        self.assertEqual(len(verify_lock(self.root)["packages"]), 2)

    def test_missing_lock(self):
        with self.assertRaisesRegex(KartError, "Missing lockfile"):
            verify_lock(self.root)

    def test_changed_manifest(self):
        lockfile = write_lock(self.root)
        original = lockfile.read_bytes()
        (self.lib / "kart.toml").write_text(
            '[package]\nname = "lib"\nversion = "1.0.1"\n', encoding="utf-8"
        )
        with self.assertRaisesRegex(KartError, "outdated"):
            verify_lock(self.root)
        self.assertEqual(lockfile.read_bytes(), original)

    def test_corrupted_lock(self):
        lockfile = write_lock(self.root)
        lockfile.write_text('{invalid', encoding="utf-8")
        with self.assertRaisesRegex(KartError, "Cannot read lockfile"):
            verify_lock(self.root)

    def test_unsupported_version(self):
        lockfile = write_lock(self.root)
        data = json.loads(lockfile.read_text(encoding="utf-8"))
        data["lock_version"] = 2
        lockfile.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(KartError, "Unsupported"):
            verify_lock(self.root)

    def test_tampered_package_entry(self):
        lockfile = write_lock(self.root)
        data = json.loads(lockfile.read_text(encoding="utf-8"))
        data["packages"][0]["manifest_sha256"] = "0" * 64
        lockfile.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(KartError, "outdated"):
            verify_lock(self.root)


if __name__ == "__main__":
    unittest.main()
