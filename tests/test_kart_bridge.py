"""Kart 14.9-14.11: explicit package paths and build preflight."""
import json
import tempfile
import unittest
from pathlib import Path
from kart.core import KartError, write_lock, install_packages, installed_packages, build_preflight


class KartBridgeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.app, self.lib, self.store = root / 'app', root / 'lib', root / 'cache'
        self.app.mkdir()
        self.lib.mkdir()
        (self.app / 'kart.toml').write_text('[package]\nname="app"\nversion="0.0.1"\n[dependencies]\nlib={path="../lib"}\n')
        (self.lib / 'kart.toml').write_text('[package]\nname="lib"\nversion="1.0.0"\n')
        (self.lib / 'math.vq').write_text('test')

    def prepare(self):
        write_lock(self.app)
        install_packages(self.app, self.store)

    def test_paths_and_preflight(self):
        self.prepare()
        self.assertEqual(installed_packages(self.app)['lib'], self.app / '.kart/packages/lib')
        self.assertEqual(build_preflight(self.app)['lib'], str(self.app / '.kart/packages/lib'))

    def test_missing_lock(self):
        install_packages(self.app, self.store)
        with self.assertRaises(KartError):
            build_preflight(self.app)

    def test_changed_manifest(self):
        self.prepare()
        (self.lib / 'kart.toml').write_text('[package]\nname="lib"\nversion="1.0.1"\n')
        with self.assertRaises(KartError):
            build_preflight(self.app)

    def test_corrupted_installation(self):
        self.prepare()
        (self.app / '.kart/packages/lib/math.vq').write_text('changed')
        with self.assertRaisesRegex(KartError, 'content mismatch'):
            build_preflight(self.app)

    def test_missing_package_from_index(self):
        self.prepare()
        path = self.app / '.kart/installed.json'
        data = json.loads(path.read_text())
        data['packages'] = []
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(KartError, 'missing'):
            build_preflight(self.app)


if __name__ == '__main__':
    unittest.main()
