"""Chapter 14.13: opt-in Kart package imports in the Visual Quar module loader."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from frontend.quar.ast_nodes import ImportStatement
from frontend.quar.module_loader import ModuleLoader, ModuleLoadError
from kart.core import write_lock, install_packages


class KartLoaderIntegrationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.app, lib, store = root / 'app', root / 'lib', root / 'store'
        self.app.mkdir()
        lib.mkdir()
        (self.app / 'kart.toml').write_text('[package]\nname="app"\nversion="0.0.1"\n[dependencies]\nlib={path="../lib"}\n')
        (lib / 'kart.toml').write_text('[package]\nname="lib"\nversion="1.0.0"\n')
        (lib / 'math.vq').write_text('')
        (self.app / 'main.vq').write_text('')
        write_lock(self.app)
        install_packages(self.app, store)

    def test_explicit_kart_module_import(self):
        loader = ModuleLoader(self.app, kart_project=self.app)
        with patch.object(loader, '_parse_file', side_effect=lambda path: [ImportStatement('lib.math', 'm')] if path.stem == 'main' else []):
            loader.load(self.app / 'main.vq')
        self.assertEqual(loader.module_bindings(self.app / 'main.vq')['m'],
                         self.app / '.kart/packages/lib/math.vq')

    def test_default_loader_does_not_search_kart(self):
        loader = ModuleLoader(self.app)
        with patch.object(loader, '_parse_file', return_value=[ImportStatement('lib.math', None)]):
            with self.assertRaisesRegex(ModuleLoadError, 'Module not found'):
                loader.load(self.app / 'main.vq')

    def test_ambiguous_local_module_rejected(self):
        (self.app / 'lib').mkdir()
        (self.app / 'lib/math.vq').write_text('')
        loader = ModuleLoader(self.app, kart_project=self.app)
        with patch.object(loader, '_parse_file', return_value=[ImportStatement('lib.math', None)]):
            with self.assertRaisesRegex(ModuleLoadError, 'Ambiguous'):
                loader.load(self.app / 'main.vq')

    def test_modified_installed_package_rejected(self):
        (self.app / '.kart/packages/lib/math.vq').write_text('changed')
        loader = ModuleLoader(self.app, kart_project=self.app)
        with patch.object(loader, '_parse_file', return_value=[ImportStatement('lib.math', None)]):
            with self.assertRaisesRegex(ModuleLoadError, 'Kart dependency error'):
                loader.load(self.app / 'main.vq')


if __name__ == '__main__':
    unittest.main()
