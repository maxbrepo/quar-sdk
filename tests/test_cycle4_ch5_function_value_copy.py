"""Cycle 4: preserve callable value semantics in all declaration profiles.

These tests consolidate existing Chapter 5 behavior in QRVM. They do not
extend the language or introduce a new intermediate representation.
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


def execute(source: str) -> tuple[str, list]:
    """Return captured stdout and the remaining QRVM operand stack."""
    program, _ = build_frontend(source)
    package = QRVMCompiler().compile(program)
    verify_bytecode(wrap_legacy_program(package))
    output = io.StringIO()
    vm = QRVM()
    with contextlib.redirect_stdout(output):
        vm.run(package)
    return output.getvalue(), vm.stack


class Cycle4Chapter5FunctionValueCopyTests(unittest.TestCase):
    def test_copied_callable_preserves_original_target(self):
        """Copying a function value does not alias the source variable slot."""
        for profile in PROFILES:
            with self.subTest(profile=profile):
                path = (ROOT / "examples" / "0.0.5" / profile / "05 types" /
                        "c4 ch5 function value copy parity.vq")
                self.assertTrue(path.is_file(), str(path))
                self.assertEqual(execute(path.read_text(encoding="utf-8")),
                                 ("42\n43\n", []))

    def test_lambda_copy_keeps_fixed_signature(self):
        """Copying a capture-free lambda retains its callable signature."""
        tails = {
            "typed": "function cb = lambda(int x)->int { return x + 1; }; "
                     "function copy = cb; int result = (copy)(41); print(result);",
            "inferred": "cb = lambda(int x)->int { return x + 1; }; "
                        "copy = cb; result = (copy)(41); print(result);",
            "mixed": "function cb = lambda(int x)->int { return x + 1; }; "
                     "copy = cb; int result = (copy)(41); print(result);",
        }
        for profile, source in tails.items():
            with self.subTest(profile=profile):
                self.assertEqual(execute(source), ("42\n", []))

    def test_signature_change_through_copy_is_rejected(self):
        """A copied function variable cannot change its established signature."""
        prefix = ("int inc(int x) { return x + 1; } "
                  "bool positive(int x) { return x > 0; } ")
        tails = {
            "typed": "function cb = &inc; function copy = cb; copy = &positive;",
            "inferred": "cb = &inc; copy = cb; copy = &positive;",
            "mixed": "function cb = &inc; copy = cb; copy = &positive;",
        }
        for profile, tail in tails.items():
            with self.subTest(profile=profile):
                with self.assertRaisesRegex(SemanticError, "Incompatible function signature"):
                    build_frontend(prefix + tail)

    def test_non_callable_assignment_through_copy_is_rejected(self):
        """No declaration profile may replace a callable with an integer."""
        prefix = "int inc(int x) { return x + 1; } "
        tails = {
            "typed": "function cb = &inc; function copy = cb; copy = 7;",
            "inferred": "cb = &inc; copy = cb; copy = 7;",
            "mixed": "function cb = &inc; copy = cb; copy = 7;",
        }
        for profile, tail in tails.items():
            with self.subTest(profile=profile):
                with self.assertRaises(SemanticError):
                    build_frontend(prefix + tail)

    def test_callable_copy_inside_function_scope(self):
        """A callback parameter can be copied into a local function variable."""
        prefix = ("int inc(int x) { return x + 1; } "
                  "int apply(function(int)->int callback, int x) { ")
        tails = {
            "typed": "function local = callback; return (local)(x); } "
                     "function cb = &inc; int result = apply(cb, 41); print(result);",
            "inferred": "local = callback; return (local)(x); } "
                        "cb = &inc; result = apply(cb, 41); print(result);",
            "mixed": "function local = callback; return (local)(x); } "
                     "function cb = &inc; result = apply(cb, 41); print(result);",
        }
        for profile, tail in tails.items():
            with self.subTest(profile=profile):
                self.assertEqual(execute(prefix + tail), ("42\n", []))


if __name__ == "__main__":
    unittest.main()
