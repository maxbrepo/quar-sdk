"""Cycle 4, Chapter 5: integration of existing callable features in QRVM.

The scope is typed parity with inferred and mixed, not new callable syntax.
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
from qrvm.instructions import OpCode
from qrvm.vm import QRVM


ROOT = Path(__file__).resolve().parents[1]
EXPECTED = "40\n42\n42\n43\n"


def run_source(source: str):
    """Execute one source and return the printed output, VM, and package."""
    program, _ = build_frontend(source)
    package = QRVMCompiler().compile(program)
    verify_bytecode(wrap_legacy_program(package))
    output = io.StringIO()
    vm = QRVM()
    with contextlib.redirect_stdout(output):
        vm.run(package)
    return output.getvalue(), vm, package


class Cycle4Chapter5IndirectCallbackIntegrationTests(unittest.TestCase):
    def test_three_profiles_have_identical_output_and_clean_stack(self):
        """Preserve typed/inferred/mixed parity for real callback chains."""
        for profile in ("typed", "inferred", "mixed"):
            with self.subTest(profile=profile):
                path = (ROOT / "examples" / "0.0.5" / profile / "05 types" /
                        "c4 ch5 indirect callback statements.vq")
                self.assertTrue(path.is_file(), str(path))
                output, vm, package = run_source(path.read_text(encoding="utf-8"))
                self.assertEqual(output, EXPECTED)
                self.assertEqual(vm.stack, [])
                self.assertTrue(any(opcode == OpCode.CALL_INDIRECT
                                    for opcode, _ in package["instructions"]))

    def test_indirect_statement_discards_nonvoid_return_value(self):
        """A discarded callback result must not leak into the VM stack."""
        source = ("int inc(int x) { return x + 1; } "
                  "function cb = &inc; (cb)(41); print((cb)(41));")
        output, vm, package = run_source(source)
        self.assertEqual(output, "42\n")
        self.assertEqual(vm.stack, [])
        self.assertIn((OpCode.CALL_INDIRECT, (1, True)), package["instructions"])
        self.assertIn((OpCode.CALL_INDIRECT, 1), package["instructions"])

    def test_void_callback_statement_does_not_push_result(self):
        """A void callback can be invoked without producing a stack value."""
        source = ("void emit(int x) { print(x); } "
                  "void forward(function(int)->void cb) { (cb)(42); } "
                  "function cb = &emit; forward(cb); (&emit)(43);")
        output, vm, _ = run_source(source)
        self.assertEqual(output, "42\n43\n")
        self.assertEqual(vm.stack, [])

    def test_incompatible_callback_is_rejected_in_each_profile(self):
        """Do not weaken function signature checks when invoking statements."""
        base = ("int inc(int x) { return x + 1; } "
                "bool positive(int x) { return x > 0; } ")
        bindings = {
            "typed": "function cb = &inc; cb = &positive; (cb)(41);",
            "inferred": "cb = &inc; cb = &positive; (cb)(41);",
            "mixed": "function cb = &inc; cb = &positive; (cb)(41);",
        }
        for profile, tail in bindings.items():
            with self.subTest(profile=profile):
                with self.assertRaisesRegex(SemanticError, "Incompatible function signature"):
                    build_frontend(base + tail)

    def test_unknown_callback_and_invalid_argument_rejected(self):
        """Standalone calls use the same semantic gate as expression calls."""
        with self.assertRaises(SemanticError):
            build_frontend("function cb = &unknown; (cb)(41);")
        with self.assertRaises(SemanticError):
            build_frontend("int inc(int x) { return x + 1; } "
                           "function cb = &inc; (cb)(\"wrong\");")


if __name__ == "__main__":
    unittest.main()
