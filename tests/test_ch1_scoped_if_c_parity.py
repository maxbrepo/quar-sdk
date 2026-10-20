"""Check QRVM/native C parity for lexical blocks across language profiles."""
import contextlib
import io
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from backend.c.codegen import CCodeGenerator
from main import build_frontend
from qrvm.compiler import QRVMCompiler
from qrvm.vm import QRVM

ROOT = Path(__file__).resolve().parents[1]


class ScopedIfCParityTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("cc"), "C compiler unavailable")
    def test_scoped_examples_match_native_c(self):
        examples = {
            "ch1 outer assignment across scopes.vq": "20\n30\n",
            "ch1 nested scope isolation.vq": "15\n10\n",
            "ch1 sibling branch scopes.vq": "1\n10\n",
        }
        for profile in ("typed", "inferred", "mixed"):
            for filename, expected in examples.items():
                with self.subTest(profile=profile, filename=filename):
                    source = ROOT / "examples" / "0.0.4" / profile / "01 primitives" / filename
                    program, types = build_frontend(source.read_text(encoding="utf-8"))
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        QRVM().run(QRVMCompiler().compile(program))
                    self.assertEqual(output.getvalue(), expected)
                    with tempfile.TemporaryDirectory() as folder:
                        c_file = Path(folder) / "scope.c"
                        executable = Path(folder) / "scope"
                        c_file.write_text(CCodeGenerator().generate(program, types), encoding="utf-8")
                        build = subprocess.run(
                            ["cc", "-std=c11", "-Wall", "-Werror", str(c_file), "-o", str(executable)],
                            capture_output=True, text=True,
                        )
                        self.assertEqual(build.returncode, 0, build.stderr)
                        result = subprocess.run([str(executable)], capture_output=True, text=True)
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertEqual(result.stdout, output.getvalue())
