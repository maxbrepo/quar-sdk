"""Tests for Kart's strict package-module path adapter."""
import tempfile
import unittest
from pathlib import Path
from kart.core import KartError, write_lock, install_packages
from kart.module_paths import resolve_package_module


class KartModulePathsTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        base = Path(temp.name)
        self.app, self.lib, self.store = base / 'app', base / 'lib', base / 'store'
        self.app.mkdir()
        self.lib.mkdir()
        (self.app / 'kart.toml').write_text('[package]\nname="app"\nversion="0.0.1"\n[dependencies]\nlib={path="../lib"}\n')
        (self.lib / 'kart.toml').write_text('[package]\nname="lib"\nversion="1.0.0"\n')
        (self.lib / 'math.vq').write_text('module')
        write_lock(self.app)
        install_packages(self.app, self.store)

    def test_existing_module(self):
        self.assertEqual(resolve_package_module(self.app, 'lib', 'math'), self.app / '.kart/packages/lib/math.vq')

    def test_unknown_package(self):
        with self.assertRaises(KartError):
            resolve_package_module(self.app, 'other', 'math')

    def test_invalid_module_name(self):
        with self.assertRaises(KartError):
            resolve_package_module(self.app, 'lib', '../math')

    def test_missing_module(self):
        with self.assertRaises(KartError):
            resolve_package_module(self.app, 'lib', 'missing')

    def test_modified_installation(self):
        (self.app / '.kart/packages/lib/math.vq').write_text('modified')
        with self.assertRaises(KartError):
            resolve_package_module(self.app, 'lib', 'math')
