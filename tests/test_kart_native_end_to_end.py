"""Kart local dependency compiled and executed through the native C backend."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from kart.core import update_local
from frontend.quar.module_loader import ModuleLoader
from frontend.quar.semantic import SemanticAnalyzer
from backend.c.codegen import CCodeGenerator

class KartNativeEndToEndTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("cc"), "C compiler unavailable")
    def test_installed_library_runs_natively(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            app, lib = root / "app", root / "lib"
            app.mkdir(); lib.mkdir()
            (app / "kart.toml").write_text('[package]\nname="app"\nversion="0.0.1"\n[dependencies]\nlib={path="../lib"}\n')
            (lib / "kart.toml").write_text('[package]\nname="lib"\nversion="1.0.0"\n')
            (lib / "math.vq").write_text('int add(int a, int b) { return a + b; }\n')
            (app / "main.vq").write_text('import lib.math;\nint result = lib.math.add(20, 22);\nprint(result);\n')
            update_local(app, root / "store")
            program = ModuleLoader(app, kart_project=app).load(app / "main.vq")
            validated = SemanticAnalyzer().analyze(program)
            c_source = CCodeGenerator().generate(validated)
            (root / "main.c").write_text(c_source)
            built = subprocess.run(["cc", "-std=c11", "-Wall", "-Werror", str(root / "main.c"), "-o", str(root / "appbin")], capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stderr)
            executed = subprocess.run([str(root / "appbin")], capture_output=True, text=True)
            self.assertEqual(executed.returncode, 0, executed.stderr)
            self.assertEqual(executed.stdout.strip(), "42")
