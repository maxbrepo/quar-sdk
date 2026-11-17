"""Cycle A/A02: execute existing typed numeric fixtures through QRVM."""
import contextlib
import io
from pathlib import Path
import unittest

from main import build_frontend
from qrvm.compiler import QRVMCompiler
from qrvm.vm import QRVM

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "examples" / "0.0.5" / "typed" / "05 types"


class TypedNumericExecutionA02(unittest.TestCase):
    def test_existing_typed_numeric_programs_execute(self):
        """Verify real frontend-to-QRVM execution, not just type registries."""
        expected = {
            "ch5 integer aliases.vq": "42\n",
            "ch5 safe widening.vq": "15\n",
            "ch5 signed boundaries.vq": "32639\n",
            "ch5 signed widening chain.vq": "-5\n",
            "ch5 typed function result.vq": "30\n",
            "c4 ch5 narrow return parity.vq": "7\n",
        }
        for filename, result in expected.items():
            with self.subTest(fixture=filename):
                path = FIXTURES / filename
                self.assertTrue(path.is_file(), str(path))
                program, _ = build_frontend(path.read_text(encoding="utf-8"))
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    QRVM().run(QRVMCompiler().compile(program))
                self.assertEqual(output.getvalue(), result)


if __name__ == "__main__":
    unittest.main()
