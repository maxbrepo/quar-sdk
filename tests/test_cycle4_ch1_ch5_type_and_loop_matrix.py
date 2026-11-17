"""Cycle 4 checkpoint 06: QRVM parity for established types and loop constructs.

These are regression tests for existing Visual Quar features. They do not
introduce language syntax, alter QIR, or expand Chapter 5 beyond its scope.
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


PROFILES = ("typed", "inferred", "mixed")


def execute(source: str) -> tuple[str, list]:
    """Return captured QRVM output and the final operand stack."""
    program, _ = build_frontend(source)
    bytecode = QRVMCompiler().compile(program)
    verify_bytecode(wrap_legacy_program(bytecode))
    vm = QRVM()
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        vm.run(bytecode)
    return output.getvalue(), vm.stack


def declarations(profile: str, declared_type: str, initial: str, derived: str) -> str:
    """Build equivalent typed, inferred, and mixed declarations."""
    if profile == "typed":
        return f"{declared_type} value = {initial}; {declared_type} result = {derived};"
    if profile == "inferred":
        return f"value = {initial}; result = {derived};"
    return f"{declared_type} value = {initial}; result = {derived};"


class Cycle4TypeAndLoopMatrixTests(unittest.TestCase):
    def test_returned_integer_widths_preserve_type_in_all_profiles(self):
        """Inferred narrow types must come from typed values, not int literals."""
        for type_name in ("i8", "i16", "i32", "i64", "u8", "u16", "u32", "u64"):
            prefix = (f"{type_name} seed() {{ return 7; }} "
                      f"{type_name} identity({type_name} x) {{ return x; }} ")
            for profile in PROFILES:
                with self.subTest(type=type_name, profile=profile):
                    source = (prefix + declarations(profile, type_name, "seed()", "identity(value)")
                              + " print(result);")
                    self.assertEqual(execute(source), ("7\n", []))

    def test_narrow_return_example_files_are_versioned_and_equivalent(self):
        """All newly introduced fixtures belong to version 0.0.5."""
        root = Path(__file__).resolve().parents[1]
        for profile in PROFILES:
            with self.subTest(profile=profile):
                path = (root / "examples" / "0.0.5" / profile / "05 types" /
                        "c4 ch5 narrow return parity.vq")
                self.assertTrue(path.is_file(), str(path))
                self.assertEqual(execute(path.read_text(encoding="utf-8")),
                                 ("7\n", []))

    def test_integer_literal_return_boundaries(self):
        """Typed return literals accept exact bounds and reject overflow."""
        valid = (
            ("i8", "-128", "-128\n"),
            ("i8", "127", "127\n"),
            ("u8", "0", "0\n"),
            ("u8", "255", "255\n"),
        )
        for type_name, literal, expected in valid:
            with self.subTest(type=type_name, literal=literal):
                self.assertEqual(execute(
                    f"{type_name} seed() {{ return {literal}; }} print(seed());"
                ), (expected, []))
        invalid = (("i8", "-129"), ("i8", "128"),
                   ("u8", "-1"), ("u8", "256"))
        for type_name, literal in invalid:
            with self.subTest(type=type_name, literal=literal):
                with self.assertRaises(SemanticError):
                    build_frontend(f"{type_name} seed() {{ return {literal}; }}")

    def test_nonliteral_return_narrowing_stays_rejected(self):
        """The contextual literal rule must not permit narrowing variables."""
        with self.assertRaises(SemanticError):
            build_frontend("i8 narrow(i16 value) { return value; }")

    def test_boolean_and_string_results_have_profile_parity(self):
        """QRVM must preserve nonnumeric results through typed/inferred locals."""
        for type_name, literal, expected in (("bool", "true", "True\n"),
                                             ("string", '"hello"', "hello\n")):
            prefix = (f"{type_name} seed() {{ return {literal}; }} "
                      f"{type_name} identity({type_name} x) {{ return x; }} ")
            for profile in PROFILES:
                with self.subTest(type=type_name, profile=profile):
                    source = (prefix + declarations(profile, type_name, "seed()", "identity(value)")
                              + " print(result);")
                    self.assertEqual(execute(source), (expected, []))

    def test_narrowing_from_function_result_is_rejected_in_all_profiles(self):
        """Inference must not bypass existing numeric narrowing restrictions."""
        prefix = "i16 wide() { return 7; } "
        tails = {
            "typed": "i8 result = wide();",
            "inferred": "value = wide(); i8 result = value;",
            "mixed": "i16 value = wide(); i8 result = value;",
        }
        for profile, tail in tails.items():
            with self.subTest(profile=profile):
                with self.assertRaises(SemanticError):
                    build_frontend(prefix + tail)

    def test_callback_returning_narrow_integer(self):
        """Callable signatures preserve the declared result type across profiles."""
        prefix = ("i8 seed(i8 x) { return x; } "
                  "i8 start() { return 7; } "
                  "i8 apply(function(i8)->i8 cb, i8 x) { return (cb)(x); } ")
        for profile in PROFILES:
            with self.subTest(profile=profile):
                binding = "function cb = &seed; " if profile != "inferred" else "cb = &seed; "
                start = "i8 value = start(); " if profile != "inferred" else "value = start(); "
                result = "i8 result = apply(cb, value); " if profile == "typed" else "result = apply(cb, value); "
                self.assertEqual(execute(prefix + binding + start + result + "print(result);"),
                                 ("7\n", []))

    def test_callback_inside_for_loop(self):
        """Counter loops retain callable results and an empty operand stack."""
        prefix = "int inc(int x) { return x + 1; } "
        for profile in PROFILES:
            with self.subTest(profile=profile):
                cb = "function cb = &inc; " if profile != "inferred" else "cb = &inc; "
                vars_ = "int i = 0; int total = 0; " if profile == "typed" else "i = 0; total = 0; "
                source = (prefix + cb + vars_ + "for (i = 0; i < 3) { total += (cb)(i); } "
                          "print(total);")
                self.assertEqual(execute(source), ("6\n", []))

    def test_callback_inside_do_while_loop(self):
        """Post-condition loops must preserve callback state and stack balance."""
        prefix = "int inc(int x) { return x + 1; } "
        for profile in PROFILES:
            with self.subTest(profile=profile):
                cb = "function cb = &inc; " if profile != "inferred" else "cb = &inc; "
                vars_ = "int i = 0; int total = 0; " if profile == "typed" else "i = 0; total = 0; "
                source = (prefix + cb + vars_ + "do { total += (cb)(i); i += 1; } "
                          "while (i < 3); print(total);")
                self.assertEqual(execute(source), ("6\n", []))

    def test_callback_inside_explicit_loop(self):
        """Explicit loops and break must preserve indirect function calls."""
        prefix = "int inc(int x) { return x + 1; } "
        for profile in PROFILES:
            with self.subTest(profile=profile):
                cb = "function cb = &inc; " if profile != "inferred" else "cb = &inc; "
                vars_ = "int i = 0; int total = 0; " if profile == "typed" else "i = 0; total = 0; "
                source = (prefix + cb + vars_ + "loop { total += (cb)(i); i += 1; "
                          "if (i >= 3) { break; } } print(total);")
                self.assertEqual(execute(source), ("6\n", []))

    def test_boolean_short_circuit_skips_callback(self):
        """Short-circuit behavior must be identical in all declaration styles."""
        prefix = "bool side(int x) { print(99); return true; } "
        for profile in PROFILES:
            with self.subTest(profile=profile):
                cb = "function cb = &side; " if profile != "inferred" else "cb = &side; "
                result = ("bool result = false and (cb)(1); " if profile == "typed"
                          else "result = false and (cb)(1); ")
                self.assertEqual(execute(prefix + cb + result + "print(result);"),
                                 ("False\n", []))


if __name__ == "__main__":
    unittest.main()
