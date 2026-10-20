"""Chapter 1 constants: source-profile parity for QRVM and native C."""
import contextlib
import io
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from main import build_frontend
from qrvm.compiler import QRVMCompiler
from qrvm.vm import QRVM
from backend.c.codegen import CCodeGenerator
from frontend.quar.errors import SemanticError

ROOT = Path(__file__).resolve().parents[1]

class ConstantProfileParityTests(unittest.TestCase):
    def test_constant_reassignment_rejected(self):
        for source in ("const int value = 3; value = 4;", "const value = 3; value = 4;"):
            with self.subTest(source=source):
                with self.assertRaises(SemanticError):
                    build_frontend(source)

    @unittest.skipUnless(shutil.which("cc"), "C compiler unavailable")
    def test_three_profiles_qrvm_and_c(self):
        for profile in ("typed", "inferred", "mixed"):
            with self.subTest(profile=profile):
                path = ROOT / "examples" / "0.0.4" / profile / "01 primitives" / "ch1 constants and assignments.vq"
                program, types = build_frontend(path.read_text(encoding="utf-8"))
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    QRVM().run(QRVMCompiler().compile(program))
                self.assertEqual(output.getvalue(), "5\n")
                c_source = CCodeGenerator().generate(program, types)
                self.assertIn("const ", c_source)
                with tempfile.TemporaryDirectory() as folder:
                    src = Path(folder) / "test.c"
                    exe = Path(folder) / "test"
                    src.write_text(c_source, encoding="utf-8")
                    built = subprocess.run(["cc", "-std=c11", "-Wall", "-Werror", str(src), "-o", str(exe)], capture_output=True, text=True)
                    self.assertEqual(built.returncode, 0, built.stderr)
                    result = subprocess.run([str(exe)], capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout, "5\n")
