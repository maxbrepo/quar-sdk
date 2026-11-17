"""Cycle 4 / Chapter 5: standalone indirect calls in typed and other profiles.

The call syntax already exists in expressions. This regression gate covers its
statement position, including void callbacks and unused non-void results.
"""

import contextlib
import io
import unittest

from frontend.quar.errors import SemanticError
from main import build_frontend
from qrvm.bytecode_verifier import BytecodeVerificationError, verify_bytecode
from qrvm.compiler import QRVMCompiler
from qrvm.instructions import OpCode
from qrvm.vm import QRVM
from qrvm.bytecode_format import wrap_legacy_program


def execute(source: str):
    """Compile and run source; return globals, VM and printed output."""
    program, _ = build_frontend(source)
    package = QRVMCompiler().compile(program)
    vm = QRVM()
    vm.functions = package["functions"]
    variables = {}
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        vm.execute(package["instructions"], variables)
    return variables, vm, output.getvalue(), package


class TypedIndirectStatementTests(unittest.TestCase):
    def test_void_callback_statement_across_profiles(self):
        prefix = (
            'void invoke(function(int)->void callback, int value) { (callback)(value); } '
        )
        tails = {
            "typed": 'function cb = lambda(int x)->void { print(x); }; invoke(cb, 42);',
            "inferred": 'cb = lambda(int x)->void { print(x); }; invoke(cb, 42);',
            "mixed": 'cb = lambda(int x)->void { print(x); }; int value = 42; invoke(cb, value);',
        }
        for profile, tail in tails.items():
            with self.subTest(profile=profile):
                _, vm, output, package = execute(prefix + tail)
                self.assertEqual(output, "42\n")
                self.assertEqual(vm.stack, [])
                verify_bytecode(wrap_legacy_program(package))

    def test_unused_nonvoid_result_does_not_leak_onto_stack(self):
        prefix = 'int increment(int x) { return x + 1; } '
        tails = {
            "typed": 'function cb = &increment; (cb)(40); int result = (cb)(41);',
            "inferred": 'cb = &increment; (cb)(40); result = (cb)(41);',
            "mixed": 'cb = &increment; (cb)(40); int result = (cb)(41);',
        }
        for profile, tail in tails.items():
            with self.subTest(profile=profile):
                variables, vm, _, package = execute(prefix + tail)
                self.assertEqual(variables["result"], 42)
                self.assertEqual(vm.stack, [])
                self.assertIn((OpCode.CALL_INDIRECT, (1, True)), package["instructions"])

    def test_direct_reference_can_be_invoked_as_statement(self):
        _, vm, output, _ = execute(
            'void emit(int x) { print(x); } (&emit)(42);'
        )
        self.assertEqual(output, "42\n")
        self.assertEqual(vm.stack, [])

    def test_invalid_indirect_statement_is_rejected_semantically(self):
        with self.assertRaises(SemanticError):
            execute('int increment(int x) { return x + 1; } '
                    'function cb = &increment; (cb)("wrong");')

    def test_destructuring_syntax_still_parses(self):
        # This existing statement must never be mistaken for an indirect call.
        from frontend.quar.lexer import Lexer
        from frontend.quar.parser import Parser
        source = '(int left, int right) = (19, 23);'
        program = Parser(Lexer(source).tokenize()).parse()
        self.assertEqual(program[0].__class__.__name__, "DestructuringDeclaration")

    def test_bytecode_verifier_rejects_invalid_discard_metadata(self):
        from qrvm.bytecode_verifier import _verify_body
        with self.assertRaises(BytecodeVerificationError):
            _verify_body([(OpCode.CALL_INDIRECT, (1, False))], "main")
        with self.assertRaises(BytecodeVerificationError):
            _verify_body([(OpCode.CALL_INDIRECT, (True, True))], "main")


if __name__ == "__main__":
    unittest.main()
