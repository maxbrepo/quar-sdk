"""Resolver tests for shared and incompatible transitive dependencies."""
import tempfile
import unittest
from pathlib import Path

from kart.core import KartError, resolve


def manifest(folder, name, version='1.0.0', dependencies=None):
    """Write a minimal local manifest for a resolver fixture."""
    folder.mkdir(parents=True, exist_ok=True)
    text = f'[package]\nname = "{name}"\nversion = "{version}"\n'
    if dependencies:
        text += '\n[dependencies]\n'
        for dependency, (path, constraint) in dependencies.items():
            text += f'{dependency} = {{ path = "{path}", version = "{constraint}" }}\n'
    (folder / 'kart.toml').write_text(text, encoding='utf-8')


class KartResolverTests(unittest.TestCase):
    def test_shared_dependency_diamond(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest(root / 'shared', 'shared', '1.5.0')
            manifest(root / 'left', 'left', dependencies={'shared': ('../shared', '>=1.0.0')})
            manifest(root / 'right', 'right', dependencies={'shared': ('../shared', '<2.0.0')})
            manifest(root / 'app', 'app', dependencies={'left': ('../left', '*'), 'right': ('../right', '*')})
            result = resolve(root / 'app')
            self.assertEqual([entry['name'] for entry in result['packages']], ['app', 'left', 'right', 'shared'])

    def test_conflicting_shared_constraints(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest(root / 'shared', 'shared', '1.5.0')
            manifest(root / 'left', 'left', dependencies={'shared': ('../shared', '>=1.0.0')})
            manifest(root / 'right', 'right', dependencies={'shared': ('../shared', '>=2.0.0')})
            manifest(root / 'app', 'app', dependencies={'left': ('../left', '*'), 'right': ('../right', '*')})
            with self.assertRaisesRegex(KartError, "Version conflict for 'shared'"):
                resolve(root / 'app')

    def test_same_name_different_sources(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest(root / 'one', 'shared')
            manifest(root / 'two', 'shared')
            manifest(root / 'app', 'app', dependencies={'shared': ('../one', '*')})
            manifest(root / 'left', 'left', dependencies={'shared': ('../two', '*')})
            manifest(root / 'app', 'app', dependencies={'shared': ('../one', '*'), 'left': ('../left', '*')})
            with self.assertRaisesRegex(KartError, "Conflicting dependency: 'shared'"):
                resolve(root / 'app')

    def test_cycle_in_shared_graph(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest(root / 'a', 'a', dependencies={'b': ('../b', '*')})
            manifest(root / 'b', 'b', dependencies={'a': ('../a', '*')})
            with self.assertRaisesRegex(KartError, 'Circular dependency'):
                resolve(root / 'a')


if __name__ == '__main__':
    unittest.main()
