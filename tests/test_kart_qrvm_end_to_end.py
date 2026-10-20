"""Kart 0.0.1: installed local package executes through QRVM."""
import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from kart.core import update_local
from frontend.quar.module_loader import ModuleLoader
from frontend.quar.semantic import SemanticAnalyzer
from qrvm.compiler import QRVMCompiler
from qrvm.vm import QRVM


class KartQRVMEndToEndTests(unittest.TestCase):
    def test_installed_library_executes_in_qrvm(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            app = root / "app"
            library = root / "lib"
            app.mkdir()
            library.mkdir()
            (app / "kart.toml").write_text(
                '[package]\nname = "app"\nversion = "0.0.1"\n'
                '[dependencies]\nlib = { path = "../lib" }\n',
                encoding="utf-8",
            )
            (library / "kart.toml").write_text(
                '[package]\nname = "lib"\nversion = "1.0.0"\n',
                encoding="utf-8",
            )
            (library / "math.vq").write_text(
                "int add(int a, int b) { return a + b; }\n",
                encoding="utf-8",
            )
            (app / "main.vq").write_text(
                "import lib.math;\n"
                "int result = lib.math.add(20, 22);\n"
                "print(result);\n",
                encoding="utf-8",
            )

            update_local(app, root / "store")
            program = ModuleLoader(app, kart_project=app).load(app / "main.vq")
            validated = SemanticAnalyzer().analyze(program)
            instructions = QRVMCompiler().compile(validated)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                QRVM().run(instructions)
            self.assertEqual(output.getvalue().strip(), "42")
