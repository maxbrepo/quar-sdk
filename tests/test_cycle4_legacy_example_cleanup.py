"""Guard against accidental deletion of historical 0.0.4 examples."""

import hashlib
from pathlib import Path
import tempfile
import unittest

from tools.cycle4_cleanup_legacy_examples import MOVED_FILES, clean


class Cycle4LegacyExampleCleanupTests(unittest.TestCase):
    def test_cleanup_is_idempotent_and_hash_guarded(self):
        """Remove only exact known checkpoint files, never changed content."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            # All files absent: repeated cleanup is safe.
            self.assertEqual(clean(root), (0, len(MOVED_FILES)))
            relative, expected_hash = MOVED_FILES[0]
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("user-modified content", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Refusing to delete"):
                clean(root)
            self.assertTrue(path.is_file())

    def test_moved_examples_exist_in_current_version(self):
        """Each obsolete path has a corresponding 0.0.5 example."""
        sdk = Path(__file__).resolve().parents[1]
        for relative, expected_hash in MOVED_FILES:
            with self.subTest(path=relative):
                new_path = sdk / relative.replace("examples/0.0.4/", "examples/0.0.5/", 1)
                self.assertTrue(new_path.is_file(), str(new_path))
                self.assertEqual(hashlib.sha256(new_path.read_bytes()).hexdigest(), expected_hash)


if __name__ == "__main__":
    unittest.main()
