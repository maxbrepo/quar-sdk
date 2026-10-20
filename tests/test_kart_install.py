"""Tests for project-local installation of local Kart dependencies."""
import json
import tempfile
import unittest
from pathlib import Path
from kart.core import KartError, install_packages


class KartInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.app = self.root / 'app'
        self.lib = self.root / 'lib'
        self.app.mkdir()
        self.lib.mkdir()
        (self.app / 'kart.toml').write_text('[package]\nname="app"\nversion="0.0.1"\n[dependencies]\nlib={path="../lib"}\n')
        (self.lib / 'kart.toml').write_text('[package]\nname="lib"\nversion="1.0.0"\n')
        (self.lib / 'math.vq').write_text('one')
        self.store = self.root / 'store'

    def test_install_local_dependency_and_index(self):
        index_path = install_packages(self.app, self.store)
        index = json.loads(index_path.read_text())
        self.assertEqual([p['name'] for p in index['packages']], ['lib'])
        self.assertEqual((self.app / '.kart/packages/lib/math.vq').read_text(), 'one')

    def test_repeat_install(self):
        self.assertEqual(install_packages(self.app, self.store), install_packages(self.app, self.store))

    def test_reinstall_updates_source(self):
        install_packages(self.app, self.store)
        (self.lib / 'math.vq').write_text('two')
        install_packages(self.app, self.store)
        self.assertEqual((self.app / '.kart/packages/lib/math.vq').read_text(), 'two')

    def test_invalid_dependency_keeps_old_install(self):
        install_packages(self.app, self.store)
        (self.lib / 'kart.toml').write_text('[package]\nname="different"\nversion="1.0.0"\n')
        with self.assertRaises(KartError):
            install_packages(self.app, self.store)
        self.assertEqual((self.app / '.kart/packages/lib/math.vq').read_text(), 'one')

    def test_unsafe_install_dir_rejected(self):
        (self.app / '.kart').symlink_to(self.lib, target_is_directory=True)
        with self.assertRaisesRegex(KartError, 'Unsafe'):
            install_packages(self.app, self.store)


if __name__ == '__main__':
    unittest.main()
