"""Runtime coverage for conditional early returns through both QIR routes."""
import ctypes
import shutil
import subprocess
import tempfile
from pathlib import Path
import unittest

from frontend.quar.ast_nodes import (Assignment, FunctionDefinition, FunctionParameter,
                                     IfStatement, Integer, ReturnStatement, Variable)
from frontend.quar.ir.builder import lower_statement
from frontend.quar.qir.ast_lowering import lower_ast_function
from frontend.quar.qir.legacy_bridge import lower_ir_function
from frontend.quar.qir.c_backend import emit_c_function
from frontend.quar.qir.validation import validate_function


@unittest.skipUnless(shutil.which("cc"), "C compiler unavailable")
class BranchReturnTests(unittest.TestCase):
    def check_routes(self, function, cases):
        for route, qir in (("direct", lower_ast_function(function)),
                           ("bridge", lower_ir_function(lower_statement(function)))):
            with self.subTest(route=route):
                validate_function(qir)
                with tempfile.TemporaryDirectory() as directory:
                    source = Path(directory) / "test.c"
                    library = Path(directory) / "test.so"
                    source.write_text(emit_c_function(qir), encoding="utf-8")
                    subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror",
                                    "-Wno-unused-parameter", "-shared", "-fPIC",
                                    str(source), "-o", str(library)],
                                   check=True, capture_output=True, timeout=15)
                    entry = getattr(ctypes.CDLL(str(library)), function.name)
                    entry.argtypes = [ctypes.c_bool, ctypes.c_int32]
                    entry.restype = ctypes.c_int32
                    for flag, value, expected in cases:
                        self.assertEqual(entry(flag, value), expected)

    def test_one_branch_returns_and_other_continues(self):
        function = FunctionDefinition("i32", "early", [FunctionParameter("bool", "flag"),
            FunctionParameter("i32", "x")], [
            IfStatement(Variable("flag"), [ReturnStatement(Integer(17))],
                        [Assignment("x", Integer(25))]),
            ReturnStatement(Variable("x"))])
        self.check_routes(function, [(True, 1, 17), (False, 1, 25)])

    def test_both_branches_return_without_final_return(self):
        function = FunctionDefinition("i32", "both", [FunctionParameter("bool", "flag"),
            FunctionParameter("i32", "x")], [
            IfStatement(Variable("flag"), [ReturnStatement(Integer(7))],
                        [ReturnStatement(Variable("x"))])])
        self.check_routes(function, [(True, 99, 7), (False, 99, 99)])

    def test_nested_return_and_fallthrough(self):
        function = FunctionDefinition("i32", "nested_early", [FunctionParameter("bool", "flag"),
            FunctionParameter("i32", "x")], [
            IfStatement(Variable("flag"), [
                IfStatement(Variable("flag"), [ReturnStatement(Integer(42))], [])],
                [Assignment("x", Integer(8))]),
            ReturnStatement(Variable("x"))])
        self.check_routes(function, [(True, 5, 42), (False, 5, 8)])


if __name__ == "__main__":
    unittest.main()
