"""Executable short-circuit regressions across both QIR lowering paths."""
import ctypes
import os
import shutil
import subprocess
import tempfile
import unittest

from frontend.quar.ast_nodes import (BinaryOperation, FunctionDefinition,
                                     FunctionParameter, Integer, ReturnStatement, Variable)
from frontend.quar.ir.builder import lower_statement
from frontend.quar.qir.ast_lowering import lower_ast_function
from frontend.quar.qir.legacy_bridge import lower_ir_function
from frontend.quar.qir.c_backend import emit_c_function


@unittest.skipUnless(shutil.which("cc"), "C compiler unavailable")
class ShortCircuitRuntimeTests(unittest.TestCase):
    def test_skipped_division_by_zero_both_lowering_paths(self):
        # The right operand traps if evaluated; short-circuit must skip it.
        dangerous = BinaryOperation(
            BinaryOperation(Variable("x"), "/", Integer(0)),
            "==", Integer(1))
        for operator, skip_value, expected in (("and", False, False), ("or", True, True)):
            ast = FunctionDefinition("bool", "short_circuit", [
                FunctionParameter("bool", "a"), FunctionParameter("int", "x")],
                [ReturnStatement(BinaryOperation(Variable("a"), operator, dangerous))])
            for path, function in (("direct", lower_ast_function(ast)),
                                   ("bridge", lower_ir_function(lower_statement(ast)))):
                with self.subTest(operator=operator, path=path):
                    with tempfile.TemporaryDirectory() as directory:
                        source = os.path.join(directory, "test.c")
                        executable = os.path.join(directory, "test")
                        with open(source, "w", encoding="utf-8") as handle:
                            handle.write(emit_c_function(function))
                            handle.write("\nint main(void) { return short_circuit(")
                            handle.write("1, 42) ? 0 : 1; }\n" if expected else
                                         "0, 42) ? 1 : 0; }\n")
                        subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror",
                                        source, "-o", executable], check=True, capture_output=True)
                        run = subprocess.run([executable], capture_output=True)
                        self.assertEqual(run.returncode, 0, run.stderr)


if __name__ == "__main__":
    unittest.main()
