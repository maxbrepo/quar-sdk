"""Regression tests for explicit boolean conditions in historical examples."""
import contextlib
import io
import unittest
from pathlib import Path

from main import build_frontend
from qrvm.compiler import QRVMCompiler
from qrvm.vm import QRVM


class LegacyTruthinessTests(unittest.TestCase):
    def test_explicit_conditions_preserve_output(self):
        root = Path(__file__).resolve().parents[1] / 'examples' / '0.0.3' / 'typed'
        expected = {
            '073': 'enabled\ndisabled\n',
            '074': 'empty\nname\nempty char\n',
            '140': 'empty\n',
        }
        for number, output in expected.items():
            with self.subTest(example=number):
                path = next(root.rglob(f'{number} *.vq'))
                program, _ = build_frontend(path.read_text(encoding='utf-8'))
                buffer = io.StringIO()
                with contextlib.redirect_stdout(buffer):
                    QRVM().run(QRVMCompiler().compile(program))
                self.assertEqual(buffer.getvalue(), output)

    def test_implicit_numeric_truthiness_stays_rejected(self):
        from frontend.quar.errors import SemanticError
        program, _ = build_frontend('i32 value = 1; if (value) { print("wrong"); }')
        with self.assertRaisesRegex((SemanticError, ValueError), 'requires bool'):
            QRVMCompiler().compile(program)
