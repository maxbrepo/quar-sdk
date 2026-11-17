"""Cycle 4: Chapter 4 loop/function interoperability across source profiles.

Only existing while loops and capture-free function references are exercised.
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


def run_source(source: str):
    """Compile, verify, and execute source; return its output and final VM stack."""
    program, _ = build_frontend(source)
    package = QRVMCompiler().compile(program)
    verify_bytecode(wrap_legacy_program(package))
    vm = QRVM()
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        vm.run(package)
    return output.getvalue(), vm.stack


class Cycle4Chapter4TypedCallbackLoopsTests(unittest.TestCase):
    def test_callback_inside_while_loop_has_profile_parity(self):
        """All declaration profiles must produce the same result and clean stack."""
        for profile in PROFILES:
            with self.subTest(profile=profile):
                path = (ROOT / "examples" / "0.0.5" / profile / "04 loops" /
                        "c4 ch4 callback loop parity.vq")
                self.assertTrue(path.is_file(), str(path))
                self.assertEqual(run_source(path.read_text(encoding="utf-8")), ("6\n", []))

    def test_callback_can_be_reassigned_before_loop(self):
        """Compatible callback reassignment must not depend on declaration style."""
        prefix = ("int inc(int x) { return x + 1; } "
                  "int plus_two(int x) { return x + 2; } "
                  "int fold(function(int)->int cb) { "
                  "int i = 0; int sum = 0; "
                  "while (i < 3) { sum = sum + (cb)(i); i = i + 1; } "
                  "return sum; } ")
        tails = {
            "typed": "function cb = &inc; cb = &plus_two; int result = fold(cb); print(result);",
            "inferred": "cb = &inc; cb = &plus_two; result = fold(cb); print(result);",
            "mixed": "function cb = &inc; cb = &plus_two; result = fold(cb); print(result);",
        }
        for profile, tail in tails.items():
            with self.subTest(profile=profile):
                self.assertEqual(run_source(prefix + tail), ("9\n", []))

    def test_void_callback_in_loop_does_not_leak_stack(self):
        """Repeated void indirect calls must not leave values on the VM stack."""
        prefix = ("void emit(int x) { print(x); } "
                  "void repeat(function(int)->void cb) { "
                  "int i = 0; while (i < 3) { (cb)(i); i = i + 1; } } ")
        tails = {
            "typed": "function cb = &emit; repeat(cb);",
            "inferred": "cb = &emit; repeat(cb);",
            "mixed": "function cb = &emit; repeat(cb);",
        }
        for profile, tail in tails.items():
            with self.subTest(profile=profile):
                self.assertEqual(run_source(prefix + tail), ("0\n1\n2\n", []))

    def test_incompatible_callback_reassignment_is_rejected(self):
        """A loop must not bypass callable signature validation."""
        prefix = ("int inc(int x) { return x + 1; } "
                  "bool positive(int x) { return x > 0; } ")
        tails = {
            "typed": "function cb = &inc; cb = &positive;",
            "inferred": "cb = &inc; cb = &positive;",
            "mixed": "function cb = &inc; cb = &positive;",
        }
        for profile, tail in tails.items():
            with self.subTest(profile=profile):
                with self.assertRaisesRegex(SemanticError, "Incompatible function signature"):
                    build_frontend(prefix + tail)

    def test_loop_callback_rejects_wrong_argument_type(self):
        """Typed callbacks cannot be invoked with an incompatible argument."""
        source = ("int inc(int x) { return x + 1; } "
                  "void run(function(int)->int cb) { "
                  "int i = 0; while (i < 1) { (cb)(\"wrong\"); i = i + 1; } } "
                  "function cb = &inc; run(cb);")
        with self.assertRaises(SemanticError):
            build_frontend(source)


if __name__ == "__main__":
    unittest.main()
