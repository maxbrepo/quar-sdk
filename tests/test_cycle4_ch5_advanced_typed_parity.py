"""Cycle 4, Chapter 5: verify existing advanced callables across profiles.

This suite is intentionally restricted to the supported Chapter 5 subset.
It does not introduce closure captures, overloads, or variadic functions.
"""

import contextlib
import io
from pathlib import Path
import unittest

from frontend.quar.errors import SemanticError
from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from frontend.quar.semantic import SemanticAnalyzer
from qrvm.compiler import QRVMCompiler
from qrvm.vm import QRVM


ROOT = Path(__file__).resolve().parents[1]
PROFILES = ("typed", "inferred", "mixed")
EXPECTED_OUTPUT = "42\n42\n120\nTrue\n42\n"


def execute(source: str) -> dict:
    """Compile and execute one source; return its global variable bindings."""
    program = Parser(Lexer(source).tokenize()).parse()
    SemanticAnalyzer().analyze(program)
    package = QRVMCompiler().compile(program)
    vm = QRVM()
    vm.functions = package["functions"]
    variables = {}
    vm.execute(package["instructions"], variables)
    return variables


class Cycle4Chapter5AdvancedTypedParityTests(unittest.TestCase):
    def test_complete_example_runs_in_all_profiles(self):
        """Verify matching observable output for all three declaration styles."""
        for profile in PROFILES:
            with self.subTest(profile=profile):
                path = (ROOT / "examples" / "0.0.5" / profile / "05 types" /
                        "c4 ch5 advanced function parity.vq")
                self.assertTrue(path.is_file())
                program = Parser(Lexer(path.read_text(encoding="utf-8")).tokenize()).parse()
                SemanticAnalyzer().analyze(program)
                package = QRVMCompiler().compile(program)
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    QRVM().run(package)
                self.assertEqual(output.getvalue(), EXPECTED_OUTPUT)

    def test_typed_local_function_reference_and_callback(self):
        """A typed function variable remains callable inside a named function."""
        base = ("int increment(int x) { return x + 1; } "
                "int apply(function(int)->int cb, int x) { return (cb)(x); } ")
        for profile, body in {
            "typed": "function cb = &increment; int value = apply(cb, x); return value;",
            "inferred": "cb = &increment; value = apply(cb, x); return value;",
            "mixed": "cb = &increment; int value = apply(cb, x); return value;",
        }.items():
            with self.subTest(profile=profile):
                source = base + "int run(int x) { " + body + " } int result = run(41);"
                self.assertEqual(execute(source)["result"], 42)

    def test_typed_reassignment_preserves_callable_signature(self):
        """Allow compatible function-value replacement in all profiles."""
        base = ("int increment(int x) { return x + 1; } "
                "int increment_twice(int x) { return x + 2; } ")
        for profile, tail in {
            "typed": "function cb = &increment; cb = &increment_twice; int result = (cb)(40);",
            "inferred": "cb = &increment; cb = &increment_twice; result = (cb)(40);",
            "mixed": "cb = &increment; cb = &increment_twice; int result = (cb)(40);",
        }.items():
            with self.subTest(profile=profile):
                self.assertEqual(execute(base + tail)["result"], 42)

    def test_typed_named_callback_and_default_argument(self):
        """Exercise existing named and default arguments with function values."""
        base = ("int increment(int x) { return x + 1; } "
                "int apply(function(int)->int cb, int x = 41) { return (cb)(x); } ")
        for profile, tail in {
            "typed": "function cb = &increment; int result = apply(x = 41, cb = cb);",
            "inferred": "cb = &increment; result = apply(x = 41, cb = cb);",
            "mixed": "cb = &increment; int result = apply(x = 41, cb = cb);",
        }.items():
            with self.subTest(profile=profile):
                self.assertEqual(execute(base + tail)["result"], 42)

    def test_bool_returning_lambda_callback(self):
        """Preserve non-integer callback return types in QRVM."""
        base = "bool check(function(int)->bool cb, int x) { return (cb)(x); } "
        for profile, tail in {
            "typed": "function cb = lambda(int x)->bool { return x > 0; }; bool result = check(cb, 1);",
            "inferred": "cb = lambda(int x)->bool { return x > 0; }; result = check(cb, 1);",
            "mixed": "cb = lambda(int x)->bool { return x > 0; }; bool result = check(cb, 1);",
        }.items():
            with self.subTest(profile=profile):
                self.assertIs(execute(base + tail)["result"], True)

    def test_incompatible_function_reassignment_rejected(self):
        """Never weaken fixed callback signature checks for typed variables."""
        base = ("int increment(int x) { return x + 1; } "
                "bool positive(int x) { return x > 0; } ")
        for profile, tail in {
            "typed": "function cb = &increment; cb = &positive; int result = (cb)(41);",
            "inferred": "cb = &increment; cb = &positive; result = (cb)(41);",
            "mixed": "cb = &increment; cb = &positive; int result = (cb)(41);",
        }.items():
            with self.subTest(profile=profile):
                with self.assertRaisesRegex(SemanticError, "Incompatible function signature"):
                    execute(base + tail)

    def test_lambda_capture_rejected_in_every_profile(self):
        """A capture-free lambda must not read enclosing local variables."""
        for profile, binding in {
            "typed": "function cb = lambda(int y)->int { return x + y; };",
            "inferred": "cb = lambda(int y)->int { return x + y; };",
            "mixed": "cb = lambda(int y)->int { return x + y; };",
        }.items():
            with self.subTest(profile=profile):
                source = "int run(int x) { " + binding + " return (cb)(1); } int result = run(41);"
                with self.assertRaises(SemanticError):
                    execute(source)


if __name__ == "__main__":
    unittest.main()
