"""QIR-08: verify complete Chapter 1 function programs across all profiles."""
from __future__ import annotations

import unittest
from pathlib import Path

from main import build_frontend
from frontend.quar.qir.program_lowering import lower_ast_program
from qrvm.compiler import QRVMCompiler
from qrvm.qir_program_backend import compile_qir_program
from tools.qir_cycle5_03_parity import execute

ROOT = Path(__file__).resolve().parents[1]


class QIR08BoolPrintParityTests(unittest.TestCase):
    def test_forward_mutual_functions_in_all_profiles(self):
        """Confirm QIR and legacy QRVM produce identical complete outputs."""
        for profile in ("typed", "inferred", "mixed"):
            with self.subTest(profile=profile):
                path = ROOT / "examples" / "0.0.5" / profile / "01 primitives" / "ch1 forward and mutual functions.vq"
                program, _ = build_frontend(path.read_text(encoding="utf-8"))
                legacy = execute(QRVMCompiler().compile(program))
                qir = lower_ast_program(program, allow_inferred_declarations=profile != "typed")
                actual = execute(compile_qir_program(qir))
                self.assertEqual(actual, legacy)
                self.assertEqual(actual, "6\nTrue\nFalse\n9\n")


if __name__ == "__main__":
    unittest.main()
