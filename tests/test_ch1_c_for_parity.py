"""Check C for-loop emission against the existing QRVM loop semantics."""
import os
import shutil
import subprocess
import tempfile
import unittest

from backend.c.codegen import CCodeGenerator
from frontend.quar.ast_nodes import (
    BinaryOperation, ForStatement, FunctionCall, Integer,
    Variable, VariableDeclaration,
)


@unittest.skipUnless(shutil.which("cc"), "A C compiler is required")
class CForParityTests(unittest.TestCase):
    def compile_and_run(self, program, *, lexical=False):
        source = CCodeGenerator().generate(program, lexical=lexical)
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "program.c")
            binary = os.path.join(directory, "program")
            with open(path, "w", encoding="utf-8") as stream:
                stream.write(source)
            subprocess.run(["cc", "-std=c11", "-Wall", "-Werror", path, "-o", binary], check=True, capture_output=True, text=True)
            return subprocess.run([binary], check=True, capture_output=True, text=True).stdout

    def test_ascending_for_counter(self):
        program = [
            VariableDeclaration("int", "i", Integer(0)),
            ForStatement("i", Integer(1), BinaryOperation(Variable("i"), "<=", Integer(3)),
                         [FunctionCall("print", [Variable("i")])]),
        ]
        self.assertEqual(self.compile_and_run(program), "1\n2\n3\n")

    def test_descending_for_counter(self):
        program = [
            VariableDeclaration("int", "i", Integer(0)),
            ForStatement("i", Integer(3), BinaryOperation(Variable("i"), ">", Integer(0)),
                         [FunctionCall("print", [Variable("i")])], step=1),
        ]
        self.assertEqual(self.compile_and_run(program), "3\n2\n1\n")

    def test_lexical_for_body_shadowing(self):
        program = [
            VariableDeclaration("int", "i", Integer(0)),
            ForStatement("i", Integer(0), BinaryOperation(Variable("i"), "<", Integer(2)),
                         [VariableDeclaration("int", "i", Integer(7)),
                          FunctionCall("print", [Variable("i")])]),
            FunctionCall("print", [Variable("i")]),
        ]
        self.assertEqual(self.compile_and_run(program, lexical=True), "7\n7\n2\n")

    def test_unknown_counter_is_rejected(self):
        program = [ForStatement("missing", Integer(0), BinaryOperation(Variable("missing"), "<", Integer(1)), [])]
        with self.assertRaisesRegex(ValueError, "Unknown for counter"):
            CCodeGenerator().generate(program)


if __name__ == "__main__":
    unittest.main()
