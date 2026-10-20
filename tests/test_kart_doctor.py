"""Read-only diagnostics for Kart projects."""
import tempfile
import unittest
from pathlib import Path
from kart.core import diagnose_project, install_packages, write_lock
from kart.__main__ import main
from contextlib import redirect_stdout
from io import StringIO

class KartDoctorTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.app = root / "app"
        self.lib = root / "lib"
        self.store = root / "store"
        self.app.mkdir()
        self.lib.mkdir()
        (self.app / "kart.toml").write_text('[package]\nname="app"\nversion="0.0.1"\n[dependencies]\nlib={path="../lib"}\n')
        (self.lib / "kart.toml").write_text('[package]\nname="lib"\nversion="1.0.0"\n')

    def test_missing_lock_and_installation(self):
        checks = diagnose_project(self.app)
        self.assertEqual([x[1] for x in checks], [True, True, False, False])
        self.assertFalse((self.app / "kart.lock").exists())
        self.assertFalse((self.app / ".kart").exists())

    def test_ready_project(self):
        write_lock(self.app)
        install_packages(self.app, self.store)
        self.assertTrue(all(item[1] for item in diagnose_project(self.app)))

    def test_modified_dependency(self):
        write_lock(self.app)
        install_packages(self.app, self.store)
        (self.lib / "kart.toml").write_text('[package]\nname="lib"\nversion="1.0.1"\n')
        self.assertEqual([x[1] for x in diagnose_project(self.app)], [True, True, False, False])

    def test_cli_exit_code(self):
        stream = StringIO()
        with redirect_stdout(stream):
            status = main(["doctor", str(self.app)])
        self.assertEqual(status, 1)
        self.assertIn("lockfile: FAIL", stream.getvalue())

if __name__ == "__main__":
    unittest.main()
