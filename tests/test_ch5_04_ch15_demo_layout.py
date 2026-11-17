"""Check the relocated Chapter 15 Python demos remain runnable."""
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
DEMOS = ROOT / 'tests' / 'ch15_tests'


class Chapter15DemoLayoutTests(unittest.TestCase):
    def test_all_demos_run_from_sdk_root(self):
        paths = sorted(DEMOS.glob('ch15_*.py'))
        self.assertEqual(len(paths), 20)
        for path in paths:
            with self.subTest(name=path.name):
                result = subprocess.run(
                    [sys.executable, str(path)], cwd=ROOT,
                    capture_output=True, text=True, timeout=30,
                )
                self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
