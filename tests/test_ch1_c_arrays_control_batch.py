"""Executable C backend coverage for fixed arrays, unary expressions and loop controls."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from backend.c.codegen import CCodeGenerator
from frontend.quar.ast_nodes import (
    ArrayAccess, ArrayAssignment, ArrayDeclaration, BinaryOperation,
    BreakStatement, ContinueStatement, ForStatement, FunctionCall, IfStatement,
    Integer, UnaryOperation, Variable, VariableDeclaration,
)


@unittest.skipUnless(shutil.which("cc"), "C compiler required")
class CArrayControlBatchTests(unittest.TestCase):
    def run_c(self, statements, *, lexical=False):
        source = CCodeGenerator().generate(statements, lexical=lexical)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "main.c"
            executable = Path(directory) / "main"
            path.write_text(source, encoding="utf-8")
            subprocess.run(["cc", "-std=c11", "-Wall", "-Werror", str(path), "-o", str(executable)],
                           check=True, capture_output=True, text=True)
            return subprocess.run([str(executable)], check=True, capture_output=True, text=True).stdout

    def test_fixed_array_read_write(self):
        statements = [ArrayDeclaration("int", "values", 3, [Integer(1), Integer(2), Integer(3)]),
                      ArrayAssignment("values", Integer(1), Integer(8)),
                      FunctionCall("print", [ArrayAccess("values", Integer(1))])]
        self.assertEqual(self.run_c(statements), "8\n")

    def test_fixed_array_lexical_shadowing(self):
        statements = [ArrayDeclaration("int", "values", 1, [Integer(2)]),
                      IfStatement(BinaryOperation(Integer(1), "==", Integer(1)),
                                  [ArrayDeclaration("int", "values", 1, [Integer(7)]),
                                   FunctionCall("print", [ArrayAccess("values", Integer(0))])], []),
                      FunctionCall("print", [ArrayAccess("values", Integer(0))])]
        self.assertEqual(self.run_c(statements, lexical=True), "7\n2\n")

    def test_unary_and_loop_control(self):
        statements = [VariableDeclaration("int", "i", Integer(0)),
                      ForStatement("i", Integer(0), BinaryOperation(Variable("i"), "<", Integer(5)),
                                   [IfStatement(BinaryOperation(Variable("i"), "==", Integer(1)),
                                                [ContinueStatement()], []),
                                    IfStatement(BinaryOperation(Variable("i"), "==", Integer(3)),
                                                [BreakStatement()], []),
                                    FunctionCall("print", [UnaryOperation("-", Variable("i"))])])]
        self.assertEqual(self.run_c(statements), "0\n-2\n")

    def test_reject_multidimensional_array(self):
        with self.assertRaisesRegex(ValueError, "one-dimensional"):
            CCodeGenerator().generate([ArrayDeclaration("int", "matrix", 2, second_size=2)])

    def test_reject_unknown_array(self):
        with self.assertRaisesRegex(ValueError, "Unknown array"):
            CCodeGenerator().generate([ArrayAssignment("missing", Integer(0), Integer(2))])


if __name__ == "__main__":
    unittest.main()
