"""Tests for Kart local dependency version constraints."""
import tempfile
import unittest
from pathlib import Path
from kart.core import KartError, matches_version, resolve, write_lock


class KartConstraintTests(unittest.TestCase):
    def test_comparisons(self):
        self.assertTrue(matches_version('1.4.0', '>=1.2.0,<2.0.0'))
        self.assertFalse(matches_version('2.0.0', '>=1.2.0,<2.0.0'))
        self.assertTrue(matches_version('1.2.0', '1.2.0'))
        self.assertTrue(matches_version('1.2.0', '*'))

    def test_invalid_constraint(self):
        with self.assertRaises(KartError):
            matches_version('1.0.0', '^1.0.0')

    def test_local_project(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lib = root / 'lib'
            lib.mkdir()
            (lib / 'kart.toml').write_text('[package]\nname="lib"\nversion="1.4.0"\n')
            (root / 'kart.toml').write_text('[package]\nname="app"\nversion="0.0.1"\n[dependencies]\nlib={path="lib",version=">=1.2.0,<2.0.0"}\n')
            self.assertEqual(len(resolve(root)['packages']), 2)
            self.assertTrue(write_lock(root).exists())
            (root / 'kart.toml').write_text('[package]\nname="app"\nversion="0.0.1"\n[dependencies]\nlib={path="lib",version=">=2.0.0"}\n')
            with self.assertRaisesRegex(KartError, 'does not satisfy'):
                resolve(root)


if __name__ == '__main__':
    unittest.main()
