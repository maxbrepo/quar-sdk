"""Local package-store regression tests for Kart 0.0.1."""
import tempfile
import unittest
from pathlib import Path
from kart.core import KartError, cache_packages, package_digest


class KartCacheTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.app = self.root / "app"
        self.lib = self.root / "lib"
        self.app.mkdir()
        self.lib.mkdir()
        (self.app / "kart.toml").write_text('[package]\nname="app"\nversion="0.0.1"\n[dependencies]\nlib={path="../lib"}\n')
        (self.lib / "kart.toml").write_text('[package]\nname="lib"\nversion="1.0.0"\n')
        (self.lib / "math.vq").write_text('print(1);\n')
        self.store = self.root / "store"

    def test_caches_local_dependency(self):
        entries = cache_packages(self.app, self.store)
        self.assertEqual(len(entries), 2)
        self.assertTrue(any((entry / "math.vq").exists() for entry in entries))

    def test_cache_reuse(self):
        self.assertEqual(cache_packages(self.app, self.store), cache_packages(self.app, self.store))

    def test_changed_source_creates_new_snapshot(self):
        first = cache_packages(self.app, self.store)
        (self.lib / "math.vq").write_text('print(2);\n')
        second = cache_packages(self.app, self.store)
        self.assertNotEqual(first, second)

    def test_corrupt_cache_rejected(self):
        entries = cache_packages(self.app, self.store)
        lib = next(entry for entry in entries if (entry / "math.vq").exists())
        (lib / "math.vq").write_text('tampered')
        with self.assertRaisesRegex(KartError, "Corrupted"):
            cache_packages(self.app, self.store)

    def test_symlink_rejected(self):
        (self.lib / "unsafe").symlink_to(self.root)
        with self.assertRaisesRegex(KartError, "Symbolic links"):
            cache_packages(self.app, self.store)

    def test_hash_ignores_lockfile(self):
        before = package_digest(self.lib)
        (self.lib / "kart.lock").write_text('temporary')
        self.assertEqual(before, package_digest(self.lib))


if __name__ == "__main__":
    unittest.main()
