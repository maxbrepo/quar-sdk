"""Execute QRVM and compiled C against the same lexical AST fixtures."""
import contextlib
import io
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from backend.c.codegen import CCodeGenerator
from frontend.quar.ast_nodes import (
    ArrayAccess, ArrayAssignment, ArrayDeclaration, BinaryOperation,
    ForStatement, FunctionCall, IfStatement, Integer, Variable,
    VariableDeclaration,
)
from main import run_qrvm


@unittest.skipUnless(shutil.which("cc"), "A C compiler is required")
class BackendParityGateTests(unittest.TestCase):
    def assert_backend_parity(self, statements, expected):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            run_qrvm(statements, lexical=True)
        lines = output.getvalue().splitlines()
        start = lines.index("=== QRVM OUTPUT ===") + 1
        end = lines.index("Program executed successfully")
        vm_lines = [line.strip() for line in lines[start:end] if line.strip()]

        generated = CCodeGenerator().generate(statements, lexical=True)
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "program.c"
            binary = Path(directory) / "program"
            source.write_text(generated, encoding="utf-8")
            build = subprocess.run(
                ["cc", "-std=c11", "-Wall", "-Werror", str(source), "-o", str(binary)],
                capture_output=True, text=True,
            )
            self.assertEqual(build.returncode, 0, build.stderr)
            result = subprocess.run([str(binary)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(vm_lines, expected)
        self.assertEqual(result.stdout.splitlines(), expected)

    def test_for_body_shadowing(self):
        self.assert_backend_parity([
            VariableDeclaration("int", "i", Integer(0)),
            ForStatement("i", Integer(0), BinaryOperation(Variable("i"), "<", Integer(2)), [
                VariableDeclaration("int", "i", Integer(7)),
                FunctionCall("print", [Variable("i")]),
            ]),
            FunctionCall("print", [Variable("i")]),
        ], ["7", "7", "2"])

    def test_array_shadowing_and_write(self):
        self.assert_backend_parity([
            ArrayDeclaration("int", "values", 1, [Integer(2)]),
            IfStatement(BinaryOperation(Integer(1), "==", Integer(1)), [
                ArrayDeclaration("int", "values", 1, [Integer(7)]),
                ArrayAssignment("values", Integer(0), Integer(8)),
                FunctionCall("print", [ArrayAccess("values", Integer(0))]),
            ], []),
            FunctionCall("print", [ArrayAccess("values", Integer(0))]),
        ], ["8", "2"])


if __name__ == "__main__":
    unittest.main()
