"""Kart local dependency regression tests (Python 3.11+)."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from kart.core import KartError, read_manifest, resolve, write_lock


class KartLocalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.app = self.root / "app"
        self.lib = self.root / "mathlib"
        self.app.mkdir()
        self.lib.mkdir()
        self.app_manifest = self.app / "kart.toml"
        self.lib_manifest = self.lib / "kart.toml"
        self.app_manifest.write_text(
            '[package]\nname = "demo_app"\nversion = "0.0.1"\n'
            '[dependencies]\nmathlib = { path = "../mathlib" }\n',
            encoding="utf-8",
        )
        self.lib_manifest.write_text(
            '[package]\nname = "mathlib"\nversion = "0.0.1"\n',
            encoding="utf-8",
        )

    def test_manifest(self) -> None:
        package = read_manifest(self.app)
        self.assertEqual((package.name, package.version), ("demo_app", "0.0.1"))

    def test_local_resolution(self) -> None:
        result = resolve(self.app)
        self.assertEqual([p["name"] for p in result["packages"]], ["demo_app", "mathlib"])

    def test_lock_is_deterministic(self) -> None:
        lock = write_lock(self.app)
        first = lock.read_bytes()
        write_lock(self.app)
        self.assertEqual(first, lock.read_bytes())
        self.assertEqual(len(json.loads(first)["packages"]), 2)

    def test_missing_dependency(self) -> None:
        self.lib.rename(self.root / "elsewhere")
        with self.assertRaisesRegex(KartError, "not found"):
            resolve(self.app)

    def test_cycle(self) -> None:
        self.lib_manifest.write_text(
            '[package]\nname = "mathlib"\nversion = "0.0.1"\n'
            '[dependencies]\ndemo_app = { path = "../app" }\n',
            encoding="utf-8",
        )
        with self.assertRaisesRegex(KartError, "Circular"):
            resolve(self.app)

    def test_dependency_name_mismatch(self) -> None:
        self.lib_manifest.write_text(
            '[package]\nname = "different"\nversion = "0.0.1"\n',
            encoding="utf-8",
        )
        with self.assertRaisesRegex(KartError, "declares package name"):
            resolve(self.app)

    def test_invalid_version(self) -> None:
        self.app_manifest.write_text('[package]\nname = "demo_app"\nversion = "abc"\n')
        with self.assertRaisesRegex(KartError, "Invalid package version"):
            resolve(self.app)


if __name__ == "__main__":
    unittest.main()
