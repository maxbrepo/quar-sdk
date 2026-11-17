"""Cycle 4: exercise existing function values in operators and conditions.

This is a QRVM parity suite; C function-value lowering is not yet covered.
"""

import contextlib
import io
from pathlib import Path
import unittest

from frontend.quar.errors import SemanticError
from main import build_frontend
from qrvm.bytecode_format import wrap_legacy_program
from qrvm.bytecode_verifier import verify_bytecode
from qrvm.compiler import QRVMCompiler
from qrvm.vm import QRVM

ROOT = Path(__file__).resolve().parents[1]
PROFILES = ("typed", "inferred", "mixed")


def execute(source: str):
    """Return stdout and stack after verified QRVM execution."""
    program, _ = build_frontend(source)
    package = QRVMCompiler().compile(program)
    verify_bytecode(wrap_legacy_program(package))
    vm = QRVM()
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        vm.run(package)
    return output.getvalue(), vm.stack


class Cycle4Chapter2Chapter3FunctionParityTests(unittest.TestCase):
    def test_chapter2_arithmetic_callback_parity(self):
        """Operators preserve precedence with indirect function results."""
        for profile in PROFILES:
            with self.subTest(profile=profile):
                path = (ROOT / "examples" / "0.0.5" / profile /
                        "02 operators expressions" / "c4 chapter2 function parity.vq")
                self.assertTrue(path.is_file(), str(path))
                self.assertEqual(execute(path.read_text(encoding="utf-8")), ("13\n", []))

    def test_chapter3_conditional_callback_parity(self):
        """Boolean callbacks can drive both branches of an existing if/else."""
        for profile in PROFILES:
            with self.subTest(profile=profile):
                path = (ROOT / "examples" / "0.0.5" / profile /
                        "03 conditions" / "c4 chapter3 function parity.vq")
                self.assertTrue(path.is_file(), str(path))
                self.assertEqual(execute(path.read_text(encoding="utf-8")),
                                 ("15\n-12\n", []))

    def test_boolean_callback_short_circuit(self):
        """The right-hand callback is skipped when the left condition is false."""
        prefix = ("bool probe(int x) { print(99); return x > 0; } "
                  "bool guard(function(int)->bool cb, bool enabled) { "
                  "if (enabled and (cb)(1)) { return true; } "
                  "return false; } ")
        tails = {
            "typed": "function cb = &probe; bool result = guard(cb, false); print(result);",
            "inferred": "cb = &probe; result = guard(cb, false); print(result);",
            "mixed": "function cb = &probe; result = guard(cb, false); print(result);",
        }
        for profile, tail in tails.items():
            with self.subTest(profile=profile):
                self.assertEqual(execute(prefix + tail), ("False\n", []))

    def test_numeric_callback_truthiness_is_preserved(self):
        """Preserve existing Chapter 3 numeric truthiness for callback results."""
        prefix = ("int increment(int x) { return x + 1; } "
                  "bool guard(function(int)->int cb) { "
                  "if ((cb)(1)) { return true; } return false; } ")
        tails = {
            "typed": "function cb = &increment; bool result = guard(cb); print(result);",
            "inferred": "cb = &increment; result = guard(cb); print(result);",
            "mixed": "function cb = &increment; bool result = guard(cb); print(result);",
        }
        for profile, tail in tails.items():
            with self.subTest(profile=profile):
                self.assertEqual(execute(prefix + tail), ("True\n", []))

    def test_callback_signature_mismatch_rejected_in_expression(self):
        """Arithmetic expressions must not bypass callable type validation."""
        prefix = ("int inc(int x) { return x + 1; } "
                  "int use(function(bool)->int cb) { return (cb)(true) + 1; } ")
        tails = {
            "typed": "function cb = &inc; int result = use(cb);",
            "inferred": "cb = &inc; result = use(cb);",
            "mixed": "function cb = &inc; result = use(cb);",
        }
        for profile, tail in tails.items():
            with self.subTest(profile=profile):
                with self.assertRaises(SemanticError):
                    build_frontend(prefix + tail)


if __name__ == "__main__":
    unittest.main()
