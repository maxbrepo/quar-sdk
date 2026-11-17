"""Executable switch lowering parity across direct AST and legacy IR routes."""
import ctypes
import os
import shutil
import subprocess
import tempfile
import unittest

from frontend.quar.ast_nodes import (Assignment, FunctionDefinition, FunctionParameter,
                                     Integer, ReturnStatement, SwitchCase, SwitchStatement, Variable)
from frontend.quar.ir.builder import lower_statement
from frontend.quar.qir.ast_lowering import QIRASTLoweringError, lower_ast_function
from frontend.quar.qir.legacy_bridge import QIRBridgeError, lower_ir_function
from frontend.quar.qir.c_backend import emit_c_function


class SwitchRuntimeTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("cc"), "C compiler unavailable")
    def test_cases_default_and_ssa_merge(self):
        function = FunctionDefinition("i32", "choose", [FunctionParameter("i32", "x"),
            FunctionParameter("i32", "result")], [
            SwitchStatement(Variable("x"), [
                SwitchCase(Integer(1), [Assignment("result", Integer(11))]),
                SwitchCase(Integer(2), [Assignment("result", Integer(22))])],
                [Assignment("result", Integer(33))]),
            ReturnStatement(Variable("result"))])
        for route, qir in (("direct", lower_ast_function(function)),
                           ("bridge", lower_ir_function(lower_statement(function)))):
            with self.subTest(route=route), tempfile.TemporaryDirectory() as directory:
                source = os.path.join(directory, "switch.c")
                library = os.path.join(directory, "switch.so")
                with open(source, "w", encoding="utf-8") as stream:
                    stream.write(emit_c_function(qir))
                subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", "-Wno-unused-parameter",
                                "-shared", "-fPIC", source, "-o", library],
                               check=True, capture_output=True, timeout=15)
                entry = ctypes.CDLL(library).choose
                entry.argtypes = [ctypes.c_int32, ctypes.c_int32]
                entry.restype = ctypes.c_int32
                for selector, expected in ((1, 11), (2, 22), (3, 33), (-1, 33)):
                    self.assertEqual(entry(selector, 99), expected)

    def test_unsupported_case_fails_closed(self):
        function = FunctionDefinition("i32", "choose", [FunctionParameter("i32", "x")], [
            SwitchStatement(Variable("x"), [SwitchCase(Variable("x"), [])], []),
            ReturnStatement(Integer(0))])
        with self.assertRaisesRegex(QIRASTLoweringError, "integer literal cases"):
            lower_ast_function(function)
        with self.assertRaisesRegex(QIRBridgeError, "integer literal cases"):
            lower_ir_function(lower_statement(function))


if __name__ == "__main__":
    unittest.main()
