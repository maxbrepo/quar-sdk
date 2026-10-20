"""Verify that Kart lockfiles survive relocation of the project tree."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from kart.core import verify_lock, write_lock


class KartPortableLockTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.project = self.base / "original" / "app"
        self.lib = self.base / "original" / "lib"
        self.project.mkdir(parents=True)
        self.lib.mkdir()
        (self.project / "kart.toml").write_text(
            '[package]\nname = "app"\nversion = "1.0.0"\n'
            '[dependencies]\nlib = { path = "../lib" }\n', encoding="utf-8"
        )
        (self.lib / "kart.toml").write_text(
            '[package]\nname = "lib"\nversion = "1.0.0"\n', encoding="utf-8"
        )

    def test_lock_paths_are_relative(self):
        locked = json.loads(write_lock(self.project).read_text())
        self.assertEqual(
            {p["name"]: p["path"] for p in locked["packages"]},
            {"app": ".", "lib": "../lib"},
        )

    def test_lock_survives_tree_relocation(self):
        original_lock = write_lock(self.project).read_bytes()
        shutil.copytree(self.base / "original", self.base / "relocated")
        relocated = self.base / "relocated" / "app"
        verify_lock(relocated)
        self.assertEqual(original_lock, (relocated / "kart.lock").read_bytes())

    def test_lock_is_deterministic_across_locations(self):
        first = write_lock(self.project).read_bytes()
        shutil.copytree(self.base / "original", self.base / "other")
        second = write_lock(self.base / "other" / "app").read_bytes()
        self.assertEqual(first, second)
