"""Function-local parameter bindings must not leak across C functions."""
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


class FunctionScopeCParityTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('cc'), 'C compiler unavailable')
    def test_function_parameter_scope_all_profiles(self):
        for profile in ('typed', 'inferred', 'mixed'):
            with self.subTest(profile=profile):
                source = ROOT / 'examples' / '0.0.4' / profile / '01 primitives' / 'ch1 function scope isolation.vq'
                program, types = build_frontend(source.read_text(encoding='utf-8'))
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    QRVM().run(QRVMCompiler().compile(program))
                self.assertEqual(output.getvalue(), '11\n22\n')
                with tempfile.TemporaryDirectory() as directory:
                    c_path = Path(directory) / 'functions.c'
                    exe_path = Path(directory) / 'functions'
                    c_path.write_text(CCodeGenerator().generate(program, types), encoding='utf-8')
                    build = subprocess.run(['cc', '-std=c11', '-Wall', '-Werror', str(c_path), '-o', str(exe_path)], capture_output=True, text=True)
                    self.assertEqual(build.returncode, 0, build.stderr)
                    run = subprocess.run([str(exe_path)], capture_output=True, text=True)
                    self.assertEqual(run.returncode, 0, run.stderr)
                    self.assertEqual(run.stdout, output.getvalue())
